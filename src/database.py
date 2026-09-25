"""把預報 JSON 攤平後存進 SQLite，並提供查詢函式。"""

import sqlite3
from pathlib import Path

import pandas as pd

from counties import COUNTIES

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "weather.db"


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


def load_forecast(path: Path = DB_PATH) -> pd.DataFrame:
    with sqlite3.connect(path) as conn:
        df = pd.read_sql("SELECT * FROM forecast", conn)
    df["lat"] = df["county"].map(lambda c: COUNTIES.get(c, (None, None, None))[0])
    df["lon"] = df["county"].map(lambda c: COUNTIES.get(c, (None, None, None))[1])
    df["region"] = df["county"].map(lambda c: COUNTIES.get(c, (None, None, "其他"))[2])
    return df
