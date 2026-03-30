import math
from typing import Dict, List

import pandas as pd

from sn_rating.helpers import resource_path
from sn_rating.datamodel import QuantInputs


def load_metadata_excel(filename: str = "sn_rating_input.xlsx") -> Dict[str, object]:
    """Read 'metadata' sheet and return core meta fields.

    Note: quantitative_weight / qualitative_weight are expected to come
    from sn_rating_config.xlsx (OTHERS sheet) via config.load_config.
    This function does NOT mutate config.
    """
    path = resource_path(filename)

    with pd.ExcelFile(path) as xls:
        df = pd.read_excel(xls, sheet_name="metadata")

    meta = dict(zip(df["field"], df["value"]))

    def flag(name: str, default: str = "TRUE") -> bool:
        """Parse boolean-like metadata values: TRUE/YES/1 → True."""
        raw = meta.get(name, default)
        s = str(raw).strip().upper()
        return s in ("TRUE", "1", "YES", "Y")

    return {
        "name": str(meta.get("name", "")).strip(),
        "country": str(meta.get("country", "")).strip(),
        "id": str(meta.get("id", "")).strip(),
        "sovereign_rating": str(meta.get("sovereign_rating", "")).strip().upper(),
        "sovereign_outlook": str(meta.get("sovereign_outlook", "")).strip(),
        "enable_peer_positioning": flag("enable_peer_positioning", "FALSE"),
        "enable_hardstops": flag("enable_hardstops", "FALSE"),
        "enable_sovereign_cap": flag("enable_sovereign_cap", "FALSE"),
    }


def df_row_to_dict(df: pd.DataFrame, col: str) -> Dict[str, float]:
    """Convert one numeric column into {row_index_as_str: float_value}."""
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
    """Thin wrapper for component columns, kept for semantic clarity."""
    return df_row_to_dict(df, col)


def df_qual_to_dict(df: pd.DataFrame, col: str) -> Dict[str, int]:
    """Convert one qualitative column into {row_index_as_str: int_score}."""
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
    """Convert peer percentile table into {metric_code: [values...]}."""
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


def load_financials_excel(filename: str = "sn_rating_input.xlsx") -> QuantInputs:
    """Read fin_ratios, components, peers_t0 from Excel into QuantInputs.

    Behavior:
    - Blank weights in fin_ratios default to 1.0 (ratio is NOT skipped).
    - Ratio values use FY25/FY24/FY23 columns.
    - Components and peers_t0 are read as in the original model.
    """
    path = resource_path(filename)

    with pd.ExcelFile(path) as xls:
        df_fin = pd.read_excel(xls, sheet_name="fin_ratios", index_col=0)
        df_comp = pd.read_excel(xls, sheet_name="components", index_col=0)
        df_peers = pd.read_excel(xls, sheet_name="peers_t0", index_col=0)

    # Clean unnamed columns if present
    df_fin = df_fin.loc[:, ~df_fin.columns.str.contains("^Unnamed")]
    df_comp = df_comp.loc[:, ~df_comp.columns.str.contains("^Unnamed")]
    df_peers = df_peers.loc[:, ~df_peers.columns.str.contains("^Unnamed")]

    # Ratio weights: blank -> 1.0
    ratio_weights: Dict[str, float] = {}
    if "weight" in df_fin.columns:
        w_series = df_fin["weight"]
        for metric, w in w_series.items():
            if w is None or (isinstance(w, float) and math.isnan(w)):
                ratio_weights[str(metric)] = 1.0
            else:
                ratio_weights[str(metric)] = float(w)
    else:
        for metric in df_fin.index:
            ratio_weights[str(metric)] = 1.0

    # Financial ratios by year
    fin_t0 = df_row_to_dict(df_fin, "FY25")
    fin_t1 = df_row_to_dict(df_fin, "FY24")
    fin_t2 = df_row_to_dict(df_fin, "FY23")

    # Components by year
    comp_t0 = components_col_to_dict(df_comp, "FY25")
    comp_t1 = components_col_to_dict(df_comp, "FY24")
    comp_t2 = components_col_to_dict(df_comp, "FY23")

    # Peers
    peers_t0 = peers_df_to_dict(df_peers)

    return QuantInputs(
        fin_t0=fin_t0,
        fin_t1=fin_t1,
        fin_t2=fin_t2,
        components_t0=comp_t0,
        components_t1=comp_t1,
        components_t2=comp_t2,
        peers_t0=peers_t0,
        ratio_weights=ratio_weights,  # if your datamodel has this field; else drop
    )