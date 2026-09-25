"""從中央氣象署 (CWA) 開放資料抓取 36 小時天氣預報。

資料集：F-C0032-001（一般天氣預報 - 今明 36 小時天氣預報）
需要 API 金鑰：到 https://opendata.cwa.gov.tw/ 註冊後取得，
並設定環境變數 CWA_API_KEY（或寫在專案根目錄的 .env）。
沒有金鑰時會改用 data/sample_forecast.json 的示範資料。
"""

import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_PATH = DATA_DIR / "forecast_raw.json"
SAMPLE_PATH = DATA_DIR / "sample_forecast.json"

API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"


def load_api_key() -> str | None:
    key = os.environ.get("CWA_API_KEY")
    if key:
        return key
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "CWA_API_KEY" and value.strip():
                return value.strip().strip('"').strip("'")
    return None


def fetch_forecast() -> tuple[dict, bool]:
    """回傳 (JSON 資料, 是否為即時資料)。"""
    key = load_api_key()
    if key:
        resp = requests.get(
            API_URL, params={"Authorization": key, "format": "JSON"}, timeout=20
        )
        resp.raise_for_status()
        data = resp.json()
        DATA_DIR.mkdir(exist_ok=True)
        RAW_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data, True
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8")), False


if __name__ == "__main__":
    data, live = fetch_forecast()
    print("即時資料" if live else "示範資料", "- 縣市數:", len(data["records"]["location"]))
