"""台灣天氣預報 Streamlit 應用。執行：streamlit run app.py"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import load_forecast, parse_forecast, save_forecast  # noqa: E402
from fetch_data import fetch_forecast  # noqa: E402

st.set_page_config(page_title="台灣天氣預報", page_icon="🌦️", layout="wide")
st.title("🌦️ 台灣天氣預報")


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
    st.map(now.dropna(subset=["lat"]), latitude="lat", longitude="lon", size=8000)
with right:
    st.subheader("各縣市最高 / 最低溫")
    st.bar_chart(now.set_index("county")[["min_temp", "max_temp"]], stack=False)

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
