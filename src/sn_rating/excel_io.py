import math
from typing import Dict, List

import pandas as pd
from sn_rating.helpers import resource_path
from sn_rating.config import RATING_WEIGHTS

def load_metadata_excel(filename: str = "sn_rating_input.xlsx") -> Dict[str, object]:
    # Always resolve relative to the exe / package folder
    path = resource_path(filename)

    with pd.ExcelFile(path) as xls:
        df = pd.read_excel(xls, sheet_name="metadata")
    meta = dict(zip(df["field"], df["value"]))

    # ADD THESE LINES HERE:
    from sn_rating.config import RATING_WEIGHTS
    q_w = meta.get("quantitative_weight")
    l_w = meta.get("qualitative_weight")
    RATING_WEIGHTS["quantitative"] = float(q_w) if pd.notna(q_w) else None
    RATING_WEIGHTS["qualitative"] = float(l_w) if pd.notna(l_w) else None
    # END ADD

    def flag(name: str, default: str = "TRUE") -> bool:
        raw = meta.get(name, default)
        s = str(raw).strip().upper()
        return s in ("TRUE", "1", "YES", "Y")

    return {
        "name": str(meta.get("name", "")).strip(),
        "country": str(meta.get("country", "")).strip(),
        "id": str(meta.get("id", "")).strip(),
        "sovereign_rating": str(meta.get("sovereign_rating", "")).strip().upper(),
        "sovereign_outlook": str(meta.get("sovereign_outlook", "")).strip(),
        "enable_peer_positioning": flag("enable_peer_positioning", "TRUE"),
        "enable_hardstops": flag("enable_hardstops", "TRUE"),
        "enable_sovereign_cap": flag("enable_sovereign_cap", "TRUE"),
    }


def df_row_to_dict(df: pd.DataFrame, col: str) -> Dict[str, float]:
    if col not in df.columns:
        return {}
    s = df[col]
    out: Dict[str, float] = {}
    for idx, v in s.items():
        try:
            if v is None or (isinstance(v, float) and math.isnan(v)):
                continue
        except TypeError:
            pass
        out[str(idx)] = float(v)
    return out


def components_col_to_dict(df: pd.DataFrame, col: str) -> Dict[str, float]:
    return df_row_to_dict(df, col)


def df_qual_to_dict(df: pd.DataFrame, col: str) -> Dict[str, int]:
    if col not in df.columns:
        return {}
    s = df[col]
    out: Dict[str, int] = {}
    for idx, v in s.items():
        try:
            if v is None or (isinstance(v, float) and math.isnan(v)):
                continue
        except TypeError:
            pass
        out[str(idx)] = int(v)
    return out


def peers_df_to_dict(df_peers: pd.DataFrame) -> Dict[str, List[float]]:
    peers: Dict[str, List[float]] = {}
    for metric, row in df_peers.iterrows():
        vals: List[float] = []
        for v in row.tolist():
            try:
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    continue
            except TypeError:
                pass
            vals.append(float(v))
        if not vals:
            continue
        peers[str(metric)] = vals
    return peers


def build_log_df(res) -> pd.DataFrame:
    from sn_rating.datamodel import RatingOutputs  # type: ignore

    rows: List[Dict[str, object]] = []

    rows.extend(res.ratio_log)

    rows.append({"Name": "", "Value": "", "Score": ""})

    rows.append({"Name": "peer_score", "Value": res.peer_score, "Score": ""})
    rows.append({"Name": "peer_underperform_count", "Value": res.peer_underperform_count, "Score": ""})
    rows.append({"Name": "peer_outperform_count", "Value": res.peer_outperform_count, "Score": ""})
    rows.append({"Name": "peer_total_compared", "Value": res.peer_total_compared, "Score": ""})

    rows.append({"Name": "combined_score", "Value": res.combined_score, "Score": ""})
    rows.append({"Name": "base_rating", "Value": res.base_rating, "Score": ""})

    rows.append({"Name": "distress_notches", "Value": res.distress_notches, "Score": ""})
    rows.append({"Name": "hardstop_rating", "Value": res.hardstop_rating, "Score": ""})

    rows.append({"Name": "band_position", "Value": res.band_position, "Score": ""})
    rows.append({"Name": "final_outlook", "Value": res.outlook, "Score": ""})

    return pd.DataFrame(rows, columns=["Name", "Value", "Score"])


def write_output_with_log(
    output_path: str,
    main_output_df: pd.DataFrame,
    res,
) -> None:
    log_df = build_log_df(res)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        main_output_df.to_excel(writer, sheet_name="output", index=False)
        log_df.to_excel(writer, sheet_name="log", index=False)
