"""台灣天氣預報 Streamlit 應用。執行：streamlit run app.py"""

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from counties import COUNTIES  # noqa: E402
from database import load_forecast, parse_forecast, save_forecast  # noqa: E402
from fetch_data import fetch_forecast  # noqa: E402

st.set_page_config(page_title="台灣天氣預報", page_icon="🌦️", layout="wide")
st.markdown(
    """
    <style>
    h1 { background: linear-gradient(90deg, #2DD4BF, #38BDF8); -webkit-background-clip: text;
         -webkit-text-fill-color: transparent; }
    h2, h3 { color: #5EEAD4; }
    [data-testid="stMetric"] { background: #11212A; border: 1px solid #1E3A44;
         border-left: 4px solid #2DD4BF; border-radius: 10px; padding: 14px 18px; }
    [data-testid="stMetricValue"] { color: #2DD4BF; }
    [data-testid="stSidebar"] { border-right: 1px solid #1E3A44; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("台灣天氣預報")


@st.cache_data(ttl=1800, show_spinner="正在取得氣象資料…")
def refresh() -> bool:
    data, live = fetch_forecast()
    save_forecast(parse_forecast(data))
    return live


try:
    live = refresh()
except Exception as exc:  # 網路或金鑰錯誤時退回示範資料
    st.error(f"抓取即時資料失敗：{exc}")
    st.stop()

if live:
    st.caption("資料來源：中央氣象署開放資料（F-C0032-001，36 小時預報）")
else:
    st.warning("目前顯示的是**示範資料**。設定環境變數 `CWA_API_KEY` 後即可顯示即時預報（見 README）。")

df = load_forecast()
periods = sorted(df["start_time"].unique())

with st.sidebar:
    st.header("篩選")
    period = st.selectbox("預報時段", periods, format_func=lambda s: s[5:16])
    regions = st.multiselect(
        "區域", ["北部", "中部", "南部", "東部", "離島"], default=["北部", "中部", "南部", "東部", "離島"]
    )
    if st.button("重新抓取資料"):
        refresh.clear()
        st.rerun()

now = df[(df["start_time"] == period) & (df["region"].isin(regions))]

c1, c2, c3 = st.columns(3)
if not now.empty:
    hottest = now.loc[now["max_temp"].idxmax()]
    coldest = now.loc[now["min_temp"].idxmin()]
    rainiest = now.loc[now["rain_prob"].idxmax()]
    c1.metric("最高溫", f"{hottest['max_temp']}°C", hottest["county"], delta_arrow="off", delta_color="off")
    c2.metric("最低溫", f"{coldest['min_temp']}°C", coldest["county"], delta_arrow="off", delta_color="off")
    c3.metric("降雨機率最高", f"{rainiest['rain_prob']}%", rainiest["county"], delta_arrow="off", delta_color="off")

left, right = st.columns([1, 1])
with left:
    st.subheader("地圖")
    st.map(now.dropna(subset=["lat"]), latitude="lat", longitude="lon", size=8000, color="#2DD4BF")
with right:
    st.subheader("各縣市溫度")
    chart_df = now.sort_values("max_temp", ascending=False).set_index("county")[["min_temp", "max_temp"]]
    st.bar_chart(
        chart_df,
        stack=False,
        horizontal=True,
        sort=False,
        color=["#38BDF8", "#2DD4BF"],
        height=max(300, 26 * len(chart_df)),
    )

st.subheader("縣市近期預報")
st.caption("ℹ️ 資料為中央氣象署「今明 36 小時天氣預報」，每個縣市只有未來 3 個 12 小時時段，不含一週以上的預報。")
county_options = [c for c in COUNTIES if c in set(df["county"])]
county = st.selectbox("選擇縣市", county_options, index=county_options.index("臺北市") if "臺北市" in county_options else 0)
county_df = df[df["county"] == county].sort_values("start_time")


def weather_icon(text: str) -> str:
    if "雨" in text:
        return "🌧️"
    if "晴" in text and "雲" not in text:
        return "☀️"
    if "晴" in text or "多雲" in text and "陰" not in text:
        return "⛅"
    return "☁️"


def period_label(row) -> str:
    start, end = pd.to_datetime(row["start_time"]), pd.to_datetime(row["end_time"])
    return f"{start.month}/{start.day} {start:%H:%M} – {end.month}/{end.day} {end:%H:%M}"


cols = st.columns(len(county_df))
for col, (_, row) in zip(cols, county_df.iterrows()):
    with col.container(border=True):
        st.caption(period_label(row))
        st.markdown(f"### {weather_icon(row['weather'])} {row['weather']}")
        st.markdown(f"**{row['min_temp']}° – {row['max_temp']}°C**")
        st.caption(f"降雨機率 {row['rain_prob']}%　·　{row['comfort']}")

trend = county_df.assign(
    時段=pd.to_datetime(county_df["start_time"]).map(lambda t: f"{t.month}/{t.day} {t:%H}時")
).rename(columns={"min_temp": "最低溫", "max_temp": "最高溫"})
trend = trend.melt(id_vars="時段", value_vars=["最低溫", "最高溫"], var_name="類型", value_name="溫度")
st.altair_chart(
    alt.Chart(trend)
    .mark_line(point=True, strokeWidth=3)
    .encode(
        x=alt.X("時段:N", sort=None, axis=alt.Axis(labelAngle=0), title=None),
        y=alt.Y("溫度:Q", scale=alt.Scale(zero=False, nice=True), title="溫度 (°C)"),
        color=alt.Color(
            "類型:N", scale=alt.Scale(domain=["最低溫", "最高溫"], range=["#38BDF8", "#2DD4BF"]), title=None
        ),
    )
    .properties(height=240),
    width="stretch",
)

st.subheader("預報明細")
st.dataframe(
    now[["county", "region", "weather", "min_temp", "max_temp", "rain_prob", "comfort"]].rename(
        columns={
            "county": "縣市",
            "region": "區域",
            "weather": "天氣",
            "min_temp": "最低溫",
            "max_temp": "最高溫",
            "rain_prob": "降雨機率(%)",
            "comfort": "舒適度",
        }
    ),
    hide_index=True,
    width="stretch",
)
