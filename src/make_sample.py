"""產生與 CWA F-C0032-001 格式相同的「示範資料」（非真實預報），供沒有 API 金鑰時使用。"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from counties import COUNTIES

OUT = Path(__file__).resolve().parent.parent / "data" / "sample_forecast.json"
REGION_BASE = {"北部": 24, "中部": 26, "南部": 27, "東部": 25, "離島": 24}
WEATHER = ["晴時多雲", "多雲", "多雲時陰", "陰短暫雨", "多雲短暫陣雨"]
COMFORT = ["舒適", "悶熱", "稍有寒意"]


def build() -> dict:
    random.seed(20260925)
    start = datetime(2026, 9, 25, 6)
    fmt = "%Y-%m-%d %H:%M:%S"
    locations = []
    for name, (_, _, region) in COUNTIES.items():
        elements = {k: [] for k in ("Wx", "PoP", "MinT", "CI", "MaxT")}
        base = REGION_BASE[region]
        for i in range(3):
            s, e = start + timedelta(hours=12 * i), start + timedelta(hours=12 * (i + 1))
            lo = base + random.randint(-2, 1)
            hi = lo + random.randint(3, 7)
            wx = random.choice(WEATHER)
            values = {
                "Wx": wx,
                "PoP": str(random.choice([0, 10, 20, 30, 50, 70]) if "雨" in wx else random.choice([0, 10, 20])),
                "MinT": str(lo),
                "CI": random.choice(COMFORT),
                "MaxT": str(hi),
            }
            for k, v in values.items():
                elements[k].append(
                    {"startTime": s.strftime(fmt), "endTime": e.strftime(fmt), "parameter": {"parameterName": v}}
                )
        locations.append(
            {
                "locationName": name,
                "weatherElement": [{"elementName": k, "time": v} for k, v in elements.items()],
            }
        )
    return {"success": "true", "records": {"datasetDescription": "示範資料（非真實預報）", "location": locations}}


if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", OUT)
