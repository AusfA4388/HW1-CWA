"""從中央氣象署 (CWA) 開放資料抓取 36 小時天氣預報。

資料集：F-C0032-001（一般天氣預報 - 今明 36 小時天氣預報）
需要 API 金鑰：到 https://opendata.cwa.gov.tw/ 註冊後取得，
並設定環境變數 CWA_API_KEY（或寫在專案根目錄的 .env）。
沒有金鑰時會改用 data/sample_forecast.json 的示範資料。
"""

import json
import os
import ssl
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter

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


class _CwaAdapter(HTTPAdapter):
    """CWA 的憑證缺少 Subject Key Identifier，Python 3.13 的嚴格檢查會拒絕。
    仍然驗證憑證鏈與主機名稱，只關閉 VERIFY_X509_STRICT，且只掛在 CWA 網域上。"""

    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
        kwargs["ssl_context"] = ctx
        super().init_poolmanager(*args, **kwargs)


def _get_live(key: str) -> dict:
    """呼叫 CWA API。錯誤訊息不含網址，避免授權碼外洩。"""
    session = requests.Session()
    session.mount("https://opendata.cwa.gov.tw", _CwaAdapter())
    try:
        resp = session.get(API_URL, params={"Authorization": key, "format": "JSON"}, timeout=20)
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(f"CWA API 回應錯誤 (HTTP {exc.response.status_code})，請檢查授權碼") from None
    except requests.RequestException as exc:
        raise RuntimeError(f"無法連線到 CWA API：{type(exc).__name__}") from None
    return resp.json()


def fetch_forecast() -> tuple[dict, bool, str | None]:
    """回傳 (JSON 資料, 是否為即時資料, 錯誤訊息)。

    有金鑰但抓取失敗（例如雲端主機連不到 CWA）時，退回示範資料並附上錯誤訊息；
    沒有金鑰時直接用示範資料，錯誤訊息為 None。錯誤訊息不含授權碼。
    """
    sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    key = load_api_key()
    if not key:
        return sample, False, None
    try:
        data = _get_live(key)
        if "records" not in data:
            raise RuntimeError("CWA API 回傳格式不符，請檢查授權碼")
    except (RuntimeError, ValueError) as exc:
        return sample, False, str(exc) if isinstance(exc, RuntimeError) else "CWA API 回傳的不是有效的 JSON"
    DATA_DIR.mkdir(exist_ok=True)
    RAW_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data, True, None


if __name__ == "__main__":
    data, live, error = fetch_forecast()
    print("即時資料" if live else "示範資料", "- 縣市數:", len(data["records"]["location"]), "| 錯誤:", error)
