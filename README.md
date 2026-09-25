# HW10-Taiwan-Weather

用 Python + 中央氣象署 (CWA) 開放資料 + SQLite + Streamlit 做的台灣天氣預報網頁。
（Antigravity × Gemini × GitHub 的 Vibe Coding 練習專案）

## 資料流程

1. `src/fetch_data.py`：抓取 CWA 36 小時預報 JSON（F-C0032-001）
2. `src/database.py`：解析 JSON，存進 SQLite（`data/weather.db`）
3. `app.py`：Streamlit 介面，含地圖、溫度長條圖、預報明細表

## 執行

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

瀏覽器開啟 http://localhost:8501。

## 取得即時資料（選用）

到 <https://opendata.cwa.gov.tw/> 註冊並取得 API 授權碼，然後任選一種方式：

- 設定環境變數 `CWA_API_KEY`
- 複製 `.env.example` 為 `.env`，填入授權碼

沒有金鑰時，程式會使用 `data/sample_forecast.json` 的**示範資料**（非真實預報，由 `src/make_sample.py` 產生）。

## 專案結構

```
Taiwan-Weather-Project/
├─ app.py
├─ requirements.txt
├─ data/            # 示範資料、SQLite（weather.db 不進版控）
└─ src/
   ├─ counties.py   # 縣市座標與區域
   ├─ fetch_data.py
   ├─ database.py
   └─ make_sample.py
```

## 下一步

加入更多 API（空氣品質）、部署到 Streamlit Cloud、優化 UI。
