import math
from typing import Dict, List

import pandas as pd
from sn_rating.helpers import resource_path
from sn_rating.config import RATING_WEIGHTS

def load_metadata_excel(filename: str = "sn_rating_input.xlsx") -> Dict[str, object]:
    """Read 'metadata' sheet, update RATING_WEIGHTS, and return core meta fields."""
    
    path = resource_path(filename)                      # Get absolute path (works in .py and .exe)

    with pd.ExcelFile(path) as xls:                     # Open workbook once, re-use handle
        df = pd.read_excel(xls, sheet_name="metadata")  # Read 'metadata' sheet into DataFrame
    
    meta = dict(zip(df["field"], df["value"]))          # Turn two columns into {field: value} dict

    # Update global rating weights from metadata (user-configurable in Excel)
    q_w = meta.get("quantitative_weight")              # Read quant weight (may be None/NaN)
    l_w = meta.get("qualitative_weight")               # Read qual weight
    
    RATING_WEIGHTS["quantitative"] = (                 # Store numeric or None in config
        float(q_w) if pd.notna(q_w) else None
    )
    RATING_WEIGHTS["qualitative"] = (                  # Same for qualitative side
        float(l_w) if pd.notna(l_w) else None
    )

    def flag(name: str, default: str = "TRUE") -> bool:
        """Parse boolean-like metadata values: TRUE/YES/1 → True."""
        raw = meta.get(name, default)                  # Get value or default string
        s = str(raw).strip().upper()                   # Normalize whitespace and case
        return s in ("TRUE", "1", "YES", "Y")          # Map common truthy strings to True

    return {                                           # Build clean, typed metadata dict
        "name": str(meta.get("name", "")).strip(),
        "country": str(meta.get("country", "")).strip(),
        "id": str(meta.get("id", "")).strip(),
        "sovereign_rating": str(meta.get("sovereign_rating", "")).strip().upper(),
        "sovereign_outlook": str(meta.get("sovereign_outlook", "")).strip(),
        "enable_peer_positioning": flag("enable_peer_positioning", "FALSE"),    # when empty, returns false as flag value
        "enable_hardstops": flag("enable_hardstops", "FALSE"),                  # when empty, returns false as flag value
        "enable_sovereign_cap": flag("enable_sovereign_cap", "FALSE"),          # when empty, returns false as flag value
    }



def df_row_to_dict(df: pd.DataFrame, col: str) -> Dict[str, float]:
    """Convert one numeric column into {row_index_as_str: float_value}."""
    
    if col not in df.columns:                 # If requested column missing, return empty
        return {}
    
    s = df[col]                               # Extract Series for the column
    out: Dict[str, float] = {}               # Output mapping: "ratio_code" → value
    
    for idx, v in s.items():                 # Iterate over index + value pairs
        try:
            if v is None or (isinstance(v, float) and math.isnan(v)):
                continue                     # Skip empty / NaN cells
        except TypeError:
            pass                             # Non-float values: skip NaN check, still allow cast
        out[str(idx)] = float(v)             # Store as float, key as string
    return out


def components_col_to_dict(df: pd.DataFrame, col: str) -> Dict[str, float]:
    """Thin wrapper for component columns, kept for semantic clarity."""
    
    return df_row_to_dict(df, col)           # Reuse numeric conversion logic


def df_qual_to_dict(df: pd.DataFrame, col: str) -> Dict[str, int]:
    """Convert one qualitative column into {row_index_as_str: int_score}."""
    
    if col not in df.columns:                # Missing column → empty dict
        return {}
    
    s = df[col]                              # Extract Series
    out: Dict[str, int] = {}                # Output mapping: "factor_code" → int score
    
    for idx, v in s.items():                # Iterate over index + value
        try:
            if v is None or (isinstance(v, float) and math.isnan(v)):
                continue                    # Skip blanks / NaNs
        except TypeError:
            pass
        out[str(idx)] = int(v)              # Store as int, key as string
    return out


def peers_df_to_dict(df_peers: pd.DataFrame) -> Dict[str, List[float]]:
    """Convert peer percentile table into {metric_code: [values...]}."""
    
    peers: Dict[str, List[float]] = {}      # Output mapping: "metric" → list of floats
    
    for metric, row in df_peers.iterrows(): # Loop each row; index is metric name/code
        vals: List[float] = []              # List of non-empty peer values
        
        for v in row.tolist():              # Iterate raw cell values across the row
            try:
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    continue                # Skip missing / NaN peers
            except TypeError:
                pass
            vals.append(float(v))           # Append numeric peer value
        
        if not vals:                        # If all values empty, skip this metric
            continue
        
        peers[str(metric)] = vals           # Store list under string metric key
    
    return peers