"""把預報 JSON 攤平後存進 SQLite，並提供查詢函式。"""

import os
import sqlite3
from pathlib import Path

import pandas as pd

from counties import COUNTIES

# 環境變數 WEATHER_DB 可指定其他資料庫檔（測試用）
DB_PATH = Path(os.environ.get("WEATHER_DB") or Path(__file__).resolve().parent.parent / "data" / "weather.db")

HISTORY_COLUMNS = ["county", "start_time", "end_time", "weather", "rain_prob", "min_temp", "max_temp", "comfort"]


def parse_forecast(data: dict) -> pd.DataFrame:
    """CWA JSON -> 每個縣市、每個時段一列。"""
    rows = []
    for loc in data["records"]["location"]:
        name = loc["locationName"]
        periods: dict[str, dict] = {}
        for element in loc["weatherElement"]:
            for t in element["time"]:
                p = periods.setdefault(
                    t["startTime"], {"start_time": t["startTime"], "end_time": t["endTime"]}
                )
                p[element["elementName"]] = t["parameter"]["parameterName"]
        for p in periods.values():
            rows.append(
                {
                    "county": name,
                    "start_time": p["start_time"],
                    "end_time": p["end_time"],
                    "weather": p.get("Wx"),
                    "rain_prob": int(p["PoP"]),
                    "min_temp": int(p["MinT"]),
                    "max_temp": int(p["MaxT"]),
                    "comfort": p.get("CI"),
                }
            )
    return pd.DataFrame(rows)


def save_forecast(df: pd.DataFrame, path: Path = DB_PATH) -> None:
    path.parent.mkdir(exist_ok=True)
    with sqlite3.connect(path) as conn:
        df.to_sql("forecast", conn, if_exists="replace", index=False)


def append_history(df: pd.DataFrame, fetched_at: str, path: Path = DB_PATH) -> bool:
    """把這次抓到的預報加進 forecast_history。內容與上一批完全相同時不重複寫入。

    回傳是否有新增。
    """
    path.parent.mkdir(exist_ok=True)
    batch = df[HISTORY_COLUMNS].sort_values(["county", "start_time"]).reset_index(drop=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS forecast_history ("
            "fetched_at TEXT, county TEXT, start_time TEXT, end_time TEXT, weather TEXT, "
            "rain_prob INTEGER, min_temp INTEGER, max_temp INTEGER, comfort TEXT)"
        )
        last = conn.execute("SELECT MAX(fetched_at) FROM forecast_history").fetchone()[0]
        if last:
            prev = pd.read_sql(
                f"SELECT {', '.join(HISTORY_COLUMNS)} FROM forecast_history WHERE fetched_at = ?",
                conn,
                params=(last,),
            )
            prev = prev.sort_values(["county", "start_time"]).reset_index(drop=True)
            if prev.equals(batch):
                return False
        batch.assign(fetched_at=fetched_at).to_sql("forecast_history", conn, if_exists="append", index=False)
    return True


def load_history(path: Path = DB_PATH) -> pd.DataFrame:
    with sqlite3.connect(path) as conn:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='forecast_history'"
        ).fetchone()
        if not exists:
            return pd.DataFrame(columns=["fetched_at", *HISTORY_COLUMNS])
        return pd.read_sql("SELECT * FROM forecast_history ORDER BY fetched_at", conn)


def load_forecast(path: Path = DB_PATH) -> pd.DataFrame:
    with sqlite3.connect(path) as conn:
        df = pd.read_sql("SELECT * FROM forecast", conn)
    df["lat"] = df["county"].map(lambda c: COUNTIES.get(c, (None, None, None))[0])
    df["lon"] = df["county"].map(lambda c: COUNTIES.get(c, (None, None, None))[1])
    df["region"] = df["county"].map(lambda c: COUNTIES.get(c, (None, None, "其他"))[2])
    return df
