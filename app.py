"""台灣天氣預報 Streamlit 應用。執行：streamlit run app.py"""

import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from counties import COUNTIES  # noqa: E402
from database import append_history, load_forecast, load_history, parse_forecast, save_forecast  # noqa: E402
from fetch_data import fetch_forecast  # noqa: E402

TEAL, BLUE = "#2DD4BF", "#38BDF8"
REGIONS = ["北部", "中部", "南部", "東部", "離島"]

# 地圖可切換的指標：欄位、色階、單位
TEMP_STOPS = [(20, "#38BDF8"), (26, "#2DD4BF"), (30, "#FACC15"), (34, "#F97316")]
RAIN_STOPS = [(0, "#475569"), (50, "#38BDF8"), (100, "#818CF8")]
MAP_METRICS = {
    "最高溫": ("max_temp", TEMP_STOPS, "°C"),
    "最低溫": ("min_temp", TEMP_STOPS, "°C"),
    "降雨機率": ("rain_prob", RAIN_STOPS, "%"),
}

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
    .tip { font-size: 0.92rem; color: #A7F3D0; margin: 2px 0; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("台灣天氣預報")


# ---------- 工具函式 ----------
def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def gradient_color(value: float, stops: list[tuple[float, str]]) -> str:
    """依色階 stops 對 value 做線性內插，回傳 #rrggbb。"""
    if value <= stops[0][0]:
        return stops[0][1]
    for (v0, c0), (v1, c1) in zip(stops, stops[1:]):
        if value <= v1:
            t = (value - v0) / (v1 - v0)
            return "#%02x%02x%02x" % tuple(round(a + (b - a) * t) for a, b in zip(_rgb(c0), _rgb(c1)))
    return stops[-1][1]


def legend_html(stops: list[tuple[float, str]], unit: str) -> str:
    lo, hi = stops[0][0], stops[-1][0]
    css = ", ".join(f"{c} {(v - lo) / (hi - lo) * 100:.0f}%" for v, c in stops)
    return (
        f'<div style="height:10px;border-radius:5px;background:linear-gradient(90deg,{css})"></div>'
        f'<div style="display:flex;justify-content:space-between;font-size:0.8rem;color:#8AA;">'
        f"<span>≤ {lo}{unit}</span><span>≥ {hi}{unit}</span></div>"
    )


def weather_icon(text: str) -> str:
    if "雨" in text:
        return "🌧️"
    if "晴" in text and "雲" not in text:
        return "☀️"
    if "晴" in text or ("多雲" in text and "陰" not in text):
        return "⛅"
    return "☁️"


def advice(row) -> list[str]:
    """依降雨機率與溫度產生帶傘、穿衣建議。"""
    tips = []
    if row.rain_prob >= 70:
        tips.append("☂️ 降雨機率高，務必帶傘")
    elif row.rain_prob >= 40:
        tips.append("🌂 可能下雨，建議帶傘")
    if row.max_temp >= 33:
        tips.append("🥵 炎熱，注意防曬與補水")
    elif row.max_temp >= 30:
        tips.append("☀️ 偏熱，穿透氣輕薄的衣物")
    if row.min_temp <= 16:
        tips.append("🧥 偏冷，記得帶外套")
    elif row.min_temp <= 20:
        tips.append("🧣 早晚稍涼，可帶薄外套")
    if row.max_temp - row.min_temp >= 8:
        tips.append("🌡️ 日夜溫差大，採洋蔥式穿搭")
    return tips or ["👕 天氣舒適，輕便穿著即可"]


def period_label(row) -> str:
    start, end = pd.to_datetime(row["start_time"]), pd.to_datetime(row["end_time"])
    return f"{start.month}/{start.day} {start:%H:%M} – {end.month}/{end.day} {end:%H:%M}"


def period_short(start_time: str) -> str:
    t = pd.to_datetime(start_time)
    return f"{t.month}/{t.day} {t:%H}時"


# ---------- 資料 ----------
@st.cache_data(ttl=1800, show_spinner="正在取得氣象資料…")
def refresh() -> tuple[bool, str]:
    data, live = fetch_forecast()
    df = parse_forecast(data)
    save_forecast(df)
    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if live:  # 示範資料不進歷史紀錄
        append_history(df, fetched_at)
    return live, fetched_at


try:
    live, fetched_at = refresh()
except Exception as exc:  # 網路或金鑰錯誤
    st.error(f"抓取即時資料失敗：{exc}")
    st.stop()

if live:
    st.caption(f"資料來源：中央氣象署開放資料（F-C0032-001，36 小時預報）　·　資料抓取時間：{fetched_at[5:16]}")
else:
    st.warning("目前顯示的是**示範資料**。設定環境變數 `CWA_API_KEY` 後即可顯示即時預報（見 README）。")

df = load_forecast()
periods = sorted(df["start_time"].unique())

with st.sidebar:
    st.header("篩選")
    period = st.selectbox("預報時段", periods, format_func=lambda s: s[5:16])
    regions = st.multiselect("區域", REGIONS, default=REGIONS)
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

tab_overview, tab_county, tab_compare, tab_table = st.tabs(["總覽", "縣市近期預報", "縣市比較", "預報明細"])

# ---------- 總覽 ----------
with tab_overview:
    left, right = st.columns([1, 1])
    with left:
        st.subheader("地圖")
        metric_name = st.radio("地圖顏色代表", list(MAP_METRICS), horizontal=True, label_visibility="collapsed")
        column, stops, unit = MAP_METRICS[metric_name]
        map_df = now.dropna(subset=["lat"]).assign(color=lambda d: d[column].map(lambda v: gradient_color(v, stops)))
        st.map(map_df, latitude="lat", longitude="lon", size=8000, color="color")
        st.markdown(legend_html(stops, unit), unsafe_allow_html=True)
    with right:
        st.subheader("各縣市溫度")
        chart_df = now.sort_values("max_temp", ascending=False).set_index("county")[["min_temp", "max_temp"]]
        st.bar_chart(
            chart_df,
            stack=False,
            horizontal=True,
            sort=False,
            color=[BLUE, TEAL],
            height=max(300, 26 * len(chart_df)),
        )

# ---------- 縣市近期預報 ----------
with tab_county:
    st.subheader("縣市近期預報")
    st.caption("ℹ️ 資料為中央氣象署「今明 36 小時天氣預報」，每個縣市只有未來 3 個 12 小時時段，不含一週以上的預報。")
    county_options = [c for c in COUNTIES if c in set(df["county"])]
    county = st.selectbox(
        "選擇縣市", county_options, index=county_options.index("臺北市") if "臺北市" in county_options else 0
    )
    county_df = df[df["county"] == county].sort_values("start_time")

    overall = SimpleNamespace(
        rain_prob=county_df["rain_prob"].max(),
        max_temp=county_df["max_temp"].max(),
        min_temp=county_df["min_temp"].min(),
    )
    st.info("**未來 36 小時建議**　" + "　｜　".join(advice(overall)))

    cols = st.columns(len(county_df))
    for col, (_, row) in zip(cols, county_df.iterrows()):
        with col.container(border=True):
            st.caption(period_label(row))
            st.markdown(f"### {weather_icon(row['weather'])} {row['weather']}")
            st.markdown(f"**{row['min_temp']}° – {row['max_temp']}°C**")
            st.caption(f"降雨機率 {row['rain_prob']}%　·　{row['comfort']}")
            for tip in advice(row):
                st.markdown(f'<div class="tip">{tip}</div>', unsafe_allow_html=True)

    trend = county_df.assign(時段=county_df["start_time"].map(period_short)).rename(
        columns={"min_temp": "最低溫", "max_temp": "最高溫"}
    )
    trend = trend.melt(id_vars="時段", value_vars=["最低溫", "最高溫"], var_name="類型", value_name="溫度")
    st.altair_chart(
        alt.Chart(trend)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X("時段:N", sort=None, axis=alt.Axis(labelAngle=0), title=None),
            y=alt.Y("溫度:Q", scale=alt.Scale(zero=False, nice=True), title="溫度 (°C)"),
            color=alt.Color(
                "類型:N", scale=alt.Scale(domain=["最低溫", "最高溫"], range=[BLUE, TEAL]), title=None
            ),
        )
        .properties(height=240),
        width="stretch",
    )

    with st.expander("預報變化紀錄（同一時段的預報，隨每次更新如何改變）"):
        history = load_history()
        hist_county = history[history["county"] == county]
        st.caption(
            f"目前累積 {history['fetched_at'].nunique()} 次預報更新。"
            "只有預報內容改變時才會記錄新的一筆（CWA 約每 6 小時更新一次）。"
        )
        target = st.selectbox("觀察的預報時段", county_df["start_time"], format_func=period_short)
        series = hist_county[hist_county["start_time"] == target]
        if series["fetched_at"].nunique() < 2:
            st.info("這個時段還沒有足夠的紀錄可比較，等預報更新後再回來看。")
        else:
            series = series.assign(抓取時間=series["fetched_at"].str[5:16]).rename(
                columns={"min_temp": "最低溫", "max_temp": "最高溫"}
            )
            series = series.melt(id_vars="抓取時間", value_vars=["最低溫", "最高溫"], var_name="類型", value_name="溫度")
            st.altair_chart(
                alt.Chart(series)
                .mark_line(point=True, strokeWidth=3)
                .encode(
                    x=alt.X("抓取時間:N", sort=None, axis=alt.Axis(labelAngle=0), title=None),
                    y=alt.Y("溫度:Q", scale=alt.Scale(zero=False, nice=True), title="預測溫度 (°C)"),
                    color=alt.Color(
                        "類型:N", scale=alt.Scale(domain=["最低溫", "最高溫"], range=[BLUE, TEAL]), title=None
                    ),
                )
                .properties(height=220),
                width="stretch",
            )

# ---------- 縣市比較 ----------
with tab_compare:
    st.subheader("縣市比較")
    picked = st.multiselect(
        "選擇要比較的縣市（最多 5 個）",
        county_options,
        default=[c for c in ("臺北市", "臺中市", "高雄市") if c in county_options],
        max_selections=5,
    )
    compare_metric = st.radio("比較項目", ["最高溫", "最低溫", "降雨機率"], horizontal=True)
    field = {"最高溫": "max_temp", "最低溫": "min_temp", "降雨機率": "rain_prob"}[compare_metric]
    unit = "%" if field == "rain_prob" else "°C"
    if not picked:
        st.info("請至少選擇一個縣市。")
    else:
        cmp_df = df[df["county"].isin(picked)].assign(時段=lambda d: d["start_time"].map(period_short))
        palette = [TEAL, BLUE, "#A78BFA", "#FBBF24", "#F472B6"]
        st.altair_chart(
            alt.Chart(cmp_df)
            .mark_line(point=True, strokeWidth=3)
            .encode(
                x=alt.X("時段:N", sort=None, axis=alt.Axis(labelAngle=0), title=None),
                y=alt.Y(f"{field}:Q", scale=alt.Scale(zero=field == "rain_prob", nice=True), title=f"{compare_metric} ({unit})"),
                color=alt.Color("county:N", scale=alt.Scale(domain=picked, range=palette[: len(picked)]), title="縣市"),
                tooltip=["county", "時段", "weather", field],
            )
            .properties(height=320),
            width="stretch",
        )
        pivot = cmp_df.pivot(index="county", columns="時段", values=field).reindex(picked)
        pivot.columns.name = None
        pivot.index.name = "縣市"
        st.dataframe(pivot.style.format("{:.0f}" + unit), width="stretch")

# ---------- 預報明細 ----------
with tab_table:
    st.subheader("預報明細")
    table = now[["county", "region", "weather", "min_temp", "max_temp", "rain_prob", "comfort"]].rename(
        columns={
            "county": "縣市",
            "region": "區域",
            "weather": "天氣",
            "min_temp": "最低溫",
            "max_temp": "最高溫",
            "rain_prob": "降雨機率(%)",
            "comfort": "舒適度",
        }
    )
    st.dataframe(table, hide_index=True, width="stretch")
    st.download_button(
        "下載 CSV",
        data=table.to_csv(index=False).encode("utf-8-sig"),  # utf-8-sig 讓 Excel 正確顯示中文
        file_name=f"taiwan_weather_{period[:10]}_{period[11:13]}h.csv",
        mime="text/csv",
    )
