import os
from datetime import datetime
from collections import defaultdict
import numpy as np
import pandas as pd
from mongo_wrapper.mongo_wrapper import MongoWrapper

STATES = [
    "MX-AGU","MX-BCN","MX-BCS","MX-CAM","MX-CHP","MX-CHH",
    "MX-COA","MX-COL","MX-DUR","MX-GUA","MX-GRO","MX-HID",
    "MX-JAL","MX-DIF","MX-MIC","MX-MOR","MX-NAY","MX-NLE",
    "MX-OAX","MX-PUE","MX-QUE","MX-ROO","MX-SLP","MX-SIN",
    "MX-SON","MX-MEX","MX-TAB","MX-TAM","MX-TLA","MX-VER",
    "MX-YUC","MX-ZAC"
]

def _extract_year(ts:int) -> int:
    return datetime.fromtimestamp(int(ts)).year

def _word_averages(raw:dict, target_years:list[int]) -> dict[int,dict[str,float]]:
    if 'interest_over_time' not in raw:
        return {}
    data = defaultdict(lambda: defaultdict(list))
    for entry in raw['interest_over_time']['timeline_data']:
        yr = _extract_year(entry['timestamp'])
        if yr in target_years:
            for v in entry['values']:
                data[yr][v['query']].append(v['extracted_value'])

    out = {}
    for yr, words in data.items():
        out[yr] = {w: round(np.mean(vals),2) if vals else 0 for w,vals in words.items()}
    return out

def _dimension_averages(word_avgs:dict[int,dict[str,float]],
                        dimensions:dict[str,list[str]]
                       ) -> dict[int,dict[str,float]]:
    out = {}
    for yr, words in word_avgs.items():
        out[yr] = {}
        for dim, kw_list in dimensions.items():
            vals = [words.get(k,0) for k in kw_list if words.get(k,0)>0]
            out[yr][dim] = round(np.mean(vals),2) if vals else 0
    return out

def run_google_trends(
    *,
    years: list[int],
    dimensions: dict[str, list[str]],
    states: list[str] = STATES,
    save_csv: bool = True,
    out_dir: str = "."
) -> dict[str, dict[int, dict[str, float]]]:
    all_kw = set(w for kws in dimensions.values() for w in kws)

    client = MongoWrapper(
        db=os.getenv("SERPAPI_DB","serpapi_5y"),
        user=os.getenv("MONGO_USERNAME"),
        password=os.getenv("MONGO_PASSWORD"),
        ip=os.getenv("MONGO_IP"),
        port=os.getenv("MONGO_PORT")
    )

    result = {}

    for st_code in states:
        buffer = defaultdict(lambda: defaultdict(list))

        for dim_kw in dimensions.values():
            coll = f"serpapi_timeseries_{st_code}_{",".join(dim_kw)}"
            try:
                docs = client.get_collection_entries(collection=coll)
            except:
                continue
            if not docs:
                continue
            raw = docs[0]
            wa = _word_averages(raw, years)
            for yr, wd in wa.items():
                for w,val in wd.items():
                    if w in all_kw:
                        buffer[yr][w].append(val)

        if buffer:
            result[st_code] = {}
            for yr in years:
                word_means = {
                    w: round(np.mean(vals),2) if vals else 0
                    for w,vals in buffer.get(yr,{}).items()
                }
                dim_means = _dimension_averages({yr:word_means}, dimensions)[yr]
                result[st_code][yr] = dim_means

    if save_csv:
        os.makedirs(out_dir, exist_ok=True)
        for yr in years:
            rows = []
            for st_code, yrs in result.items():
                row = {"state": st_code}
                row.update(yrs.get(yr, {}))
                rows.append(row)
            df = pd.DataFrame(rows).fillna(0)
            df.to_csv(os.path.join(out_dir, f"gt_{yr}.csv"), index=False)

    return result
