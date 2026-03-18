from typing import Literal, Optional, List

import warnings
import pandas as pd

from sn_rating.helpers import input_path, BandConfig
from sn_rating.datamodel import QuantInputs, QualInputs
from sn_rating.model import RatingModel
from sn_rating.excel_io import (
    load_metadata_excel,
    components_col_to_dict,
    peers_df_to_dict,
)


def _infer_time_labels(df: pd.DataFrame, drop_cols: List[str] = None) -> List[str]:
    """
    Infer [t0, t1, t2] labels from DataFrame columns,
    excluding drop_cols and any 'Unnamed' columns.
    """
    if drop_cols is None:
        drop_cols = ["metric", "weight"]           # Default for fin_ratios layout

    cols = [
        c
        for c in df.columns
        if str(c).strip().lower() not in {*(s.lower() for s in drop_cols)}
        and not str(c).startswith("Unnamed")
    ]                                              # Keeps only actual period columns

    if len(cols) < 2:
        raise ValueError("Need at least two period columns")

    t0 = cols[0]                                   # Most recent period
    t1 = cols[1]                                   # Previous period
    t2 = cols[2] if len(cols) >= 3 else cols[1]    # Fallback: reuse t1 if no t2

    return [str(t0), str(t1), str(t2)]



def run_from_excel_with_bands(
    horizon: Literal["t0", "t1", "t2"] = "t0",
):
    """
    High-level runner for the V3 model.

    Excel files are taken from the project root input folder:
      - input/sn_rating_config.xlsx (bands/config)
      - input/sn_rating_input.xlsx (user-edited input)
    """
    # Resolve input file paths
    rating_input_file = input_path("sn_rating_input.xlsx")
    config_file = input_path("sn_rating_config.xlsx")

    # Load band configuration (score tables) and global metadata
    bands = BandConfig(config_path=config_file)
    meta = load_metadata_excel(rating_input_file)

    raw_name = str(meta.get("name", "")).strip()
    cp_name = raw_name.title()                     # Title-case issuer name
    meta["name"] = cp_name                         # Normalize in metadata

    # Read all input sheets with warnings suppressed for openpyxl
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
        with pd.ExcelFile(rating_input_file) as xls:
            df_fin = pd.read_excel(xls, sheet_name="fin_ratios")
            df_comp = pd.read_excel(xls, sheet_name="components", index_col=0)
            df_qual = pd.read_excel(xls, sheet_name="qual_factors")
            df_peers_raw = pd.read_excel(xls, sheet_name="peers_t0")

    # Drop helper/empty 'Unnamed' columns
    df_fin = df_fin.loc[:, ~df_fin.columns.str.contains("^Unnamed")]
    df_qual = df_qual.loc[:, ~df_qual.columns.str.contains("^Unnamed")]
    df_peers_raw = df_peers_raw.loc[:, ~df_peers_raw.columns.str.contains("^Unnamed")]

    # ---------- FINANCIAL RATIOS (metric, weight, FYxx...) ----------
    YEAR_T0, YEAR_T1, YEAR_T2 = _infer_time_labels(
        df_fin,
        drop_cols=["metric", "weight"],
    )

    fin_t0 = {row["metric"]: row[YEAR_T0] for _, row in df_fin.iterrows()}
    fin_t1 = {row["metric"]: row[YEAR_T1] for _, row in df_fin.iterrows()}
    fin_t2 = {row["metric"]: row[YEAR_T2] for _, row in df_fin.iterrows()}

    ratio_weights = {
        row["metric"]: (row["weight"] if pd.notna(row.get("weight")) else 1.0)
        for _, row in df_fin.iterrows()
    }                                              # Per-ratio weight (default 1.0)

    # ---------- ALTMAN COMPONENTS ----------
    comp_t0 = components_col_to_dict(df_comp, YEAR_T0)  # Map code → value
    comp_t1 = components_col_to_dict(df_comp, YEAR_T1)
    comp_t2 = components_col_to_dict(df_comp, YEAR_T2)

    # ---------- QUAL FACTORS (factor, weight, bucket, FYxx...) ----------
    YEAR_Q0, YEAR_Q1, YEAR_Q2 = _infer_time_labels(
        df_qual,
        drop_cols=["factor", "weight", "bucket"],
    )

    qual_t0 = {row["factor"]: row[YEAR_Q0] for _, row in df_qual.iterrows()}
    qual_t1 = {row["factor"]: row[YEAR_Q1] for _, row in df_qual.iterrows()}

    qual_weights = {
        row["factor"]: (row["weight"] if pd.notna(row.get("weight")) else 1.0)
        for _, row in df_qual.iterrows()
    }
    qual_buckets = {
        row["factor"]: (
            row["bucket"]
            if pd.notna(row.get("bucket")) and str(row["bucket"]).strip()
            else "OTHERS"
        )
        for _, row in df_qual.iterrows()
    }

    # ---------- PEERS: use all peer columns after first (metric) ----------
    if not df_peers_raw.empty:
        first_col = df_peers_raw.columns[0]
        df_peers_raw.rename(columns={first_col: "metric"}, inplace=True)
        df_peers_raw.set_index("metric", inplace=True)
        df_peers = df_peers_raw                             # Now index = metric code
    else:
        df_peers = pd.DataFrame()

    peers_t0 = peers_df_to_dict(df_peers) if not df_peers.empty else {}  # "metric" → [values]

    # ---------- BUILD INPUT DATACLASSES ----------
    q_inputs = QuantInputs(
        fin_t0=fin_t0,
        fin_t1=fin_t1,
        fin_t2=fin_t2,
        components_t0=comp_t0,
        components_t1=comp_t1,
        components_t2=comp_t2,
        peers_t0=peers_t0,
    )

    qual_inputs = QualInputs(
        factors_t0=qual_t0,
        factors_t1=qual_t1,
    )

    # Instantiate model with issuer name and band config
    model = RatingModel(cp_name, bands)

    # Feature flags from metadata (with sane defaults)
    enable_hardstops = meta["enable_hardstops"]
    enable_sovereign_cap = meta["enable_sovereign_cap"]
    enable_peer_positioning = meta["enable_peer_positioning"]

    # Sovereign inputs: clean empty strings → None
    sovereign_rating: Optional[str] = (meta.get("sovereign_rating") or "").strip() or None
    sovereign_outlook: Optional[str] = (meta.get("sovereign_outlook") or "").strip() or None

    # ---------- RUN MODEL ----------
    res = model.compute_final_rating(
        quant_inputs=q_inputs,
        qual_inputs=qual_inputs,
        sovereign_rating=sovereign_rating,
        sovereign_outlook=sovereign_outlook,
        enable_hardstops=enable_hardstops,
        enable_sovereign_cap=enable_sovereign_cap,
        enable_peer_positioning=enable_peer_positioning,
        ratio_weights=ratio_weights,
        qual_weights=qual_weights,
        qual_buckets=qual_buckets,
    )

    return res                                     # RatingOutputs dataclass