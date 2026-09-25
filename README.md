# HW1-CWA：台灣天氣預報

用 Python + 中央氣象署 (CWA) 開放資料 + SQLite + Streamlit 做的台灣天氣預報網頁。
（Antigravity × Gemini × GitHub 的 Vibe Coding 練習專案）

## 資料流程

1. `src/fetch_data.py`：抓取 CWA 36 小時預報 JSON（F-C0032-001）
2. `src/database.py`：解析 JSON，存進 SQLite（`data/weather.db`）
3. `app.py`：Streamlit 介面，含地圖、溫度長條圖、預報明細表

## 功能

- **總覽**：全台地圖，圓點顏色可切換為最高溫、最低溫或降雨機率；各縣市溫度橫向長條圖
- **縣市近期預報**：選一個縣市看未來 36 小時的 3 個時段，附帶傘與穿衣建議、溫度趨勢；可展開「預報變化紀錄」看同一時段的預報每次更新如何改變
- **縣市比較**：最多 5 個縣市，比較最高溫、最低溫或降雨機率
- **預報明細**：完整表格，可下載 CSV（Excel 可直接開啟中文）
- 頁面顯示資料抓取時間；預報內容有變動時，會自動累積到 SQLite 的 `forecast_history` 資料表

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

抓取即時資料失敗（金鑰錯誤、網路不通、被擋）時，網頁會顯示警告並退回示範資料，不會當掉。

## 部署到 Streamlit Community Cloud

1. 到 <https://share.streamlit.io> 用 GitHub 登入，Create app，選這個 repo、分支 `main`、主檔案 `app.py`
2. Advanced settings → Secrets，填入（授權碼不要放進 repo）：

   ```toml
   CWA_API_KEY = "你的授權碼"
   ```

3. Deploy。注意：雲端檔案系統是暫時的，`weather.db` 在重啟後會清空，所以「預報變化紀錄」無法長期累積。

## 資料限制

使用的資料集 F-C0032-001 是「今明 36 小時天氣預報」：

- 每個縣市只有未來 **3 個 12 小時時段**，「縣市近期預報」也只能顯示這 3 個時段。
- 不含一週以上的預報；若要一週預報，需另外串接 CWA 的「一週天氣預報」資料集。
- 預報約每 6 小時更新，程式快取 30 分鐘，可按側邊欄「重新抓取資料」立即更新。

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
