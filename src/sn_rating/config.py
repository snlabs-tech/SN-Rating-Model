# sn_rating/config.py

import logging
import os
from typing import Dict, List, Tuple, Any, Optional, Set

import pandas as pd


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _input_path(relative_name: str) -> str:
    return os.path.join(_project_root(), "input", relative_name)


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("sn_rating")


# ---------------- DEFAULTS (single source of truth) ----------------

DEFAULT_SCORE_TO_RATING: List[Tuple[float, str]] = [
    (95.0, "AAA"),
    (90.0, "AA+"),
    (85.0, "AA"),
    (80.0, "AA-"),
    (75.0, "A+"),
    (70.0, "A"),
    (65.0, "A-"),
    (60.0, "BBB+"),
    (55.0, "BBB"),
    (50.0, "BBB-"),
    (45.0, "BB+"),
    (40.0, "BB"),
    (35.0, "BB-"),
    (30.0, "B+"),
    (25.0, "B"),
    (20.0, "B-"),
    (15.0, "CCC+"),
    (10.0, "CCC"),
    (5.0, "CCC-"),
    (2.0, "CC"),
    (0.0, "C"),
]


def derive_rating_scale(score_to_rating: List[Tuple[float, str]]) -> List[str]:
    ratings_in_order: List[str] = []
    seen: Set[str] = set()
    for thr, rat in sorted(score_to_rating, key=lambda x: x[0], reverse=True):
        if rat not in seen:
            ratings_in_order.append(rat)
            seen.add(rat)
    return ratings_in_order


DEFAULT_RATING_SCALE: List[str] = derive_rating_scale(DEFAULT_SCORE_TO_RATING)

# None ⇒ model infers weights from counts
DEFAULT_RATING_WEIGHTS: Dict[str, Optional[float]] = {
    "quantitative": None,
    "qualitative": None,
}

DEFAULT_DISTRESS_BANDS: Dict[str, List[Tuple[float, int]]] = {
    "interest_coverage": [(0.5, -4), (0.8, -3), (1.0, -2)],
    "dscr": [(0.8, -3), (0.9, -2), (1.0, -1)],
    "altman_z": [(1.2, -4), (1.5, -3), (1.81, -2)],
}

DEFAULT_MAX_DISTRESS_NOTCHES: int = -4

DEFAULT_QUAL_SCORE_SCALE: Dict[int, float] = {
    5: 100.0,
    4: 75.0,
    3: 50.0,
    2: 25.0,
    1: 0.0,
}

# These defaults should match your existing repo; abridged here for brevity.
DEFAULT_RATIOS_LOWER_BETTER: Dict[str, Dict[str, List[Tuple[float, float, float]]]] = {
    "leverage": {
        "debt_ebitda": [
            (-1e9, 2.0, 100.0),
            (2.0, 3.0, 75.0),
            (3.0, 4.0, 50.0),
            (4.0, 6.0, 25.0),
            (6.0, 1e9, 0.0),
        ],
        "net_debt_ebitda": [
            (-1e9, 1.5, 100.0),
            (1.5, 3.0, 75.0),
            (3.0, 4.5, 50.0),
            (4.5, 6.0, 25.0),
            (6.0, 1e9, 0.0),
        ],
        "debt_equity": [
            (-1e9, 0.5, 100.0),
            (0.5, 1.0, 75.0),
            (1.0, 2.0, 50.0),
            (2.0, 4.0, 25.0),
            (4.0, 1e9, 0.0),
        ],
        "debt_capital": [
            (-1e9, 0.2, 100.0),
            (0.2, 0.35, 75.0),
            (0.35, 0.5, 50.0),
            (0.5, 0.7, 25.0),
            (0.7, 1e9, 0.0),
        ],
    },
   
}

DEFAULT_RATIOS_HIGHER_BETTER: Dict[str, Dict[str, List[Tuple[float, float, float]]]] = {
    "leverage_rev": {
        "ffo_debt": [
            (0.40, 1e9, 100.0),
            (0.25, 0.40, 75.0),
            (0.12, 0.25, 50.0),
            (0.0, 0.12, 25.0),
            (-1e9, 0.0, 0.0),
        ],
        "fcf_debt": [
            (0.20, 1e9, 100.0),
            (0.10, 0.20, 75.0),
            (0.0, 0.10, 50.0),
            (-0.10, 0.0, 25.0),
            (-1e9, -0.10, 0.0),
        ],
        "interest_coverage": [
        (8.0, float("inf"), 100),
        (5.0, 8.0, 75),
        (3.0, 5.0, 50),
        (1.5, 3.0, 25),
        (float("-inf"), 1.5, 0),
        ],
        "fixed_charge_coverage": [
            (6.0, float("inf"), 100),
            (4.0, 6.0, 75),
            (2.5, 4.0, 50),
            (1.5, 2.5, 25),
            (float("-inf"), 1.5, 0),
        ],
        "dscr": [
            (2.0, float("inf"), 100),
            (1.5, 2.0, 75),
            (1.2, 1.5, 50),
            (1.0, 1.2, 25),
            (float("-inf"), 1.0, 0),
        ],
        "ebitda_margin": [
        (0.25, float("inf"), 100),
        (0.15, 0.25, 75),
        (0.10, 0.15, 50),
        (0.05, 0.10, 25),
        (float("-inf"), 0.05, 0),
        ],
        "ebit_margin": [
            (0.15, float("inf"), 100),
            (0.10, 0.15, 75),
            (0.05, 0.10, 50),
            (0.0, 0.05, 25),
            (float("-inf"), 0.0, 0),
        ],
        "roa": [
            (0.12, float("inf"), 100),
            (0.08, 0.12, 75),
            (0.04, 0.08, 50),
            (0.0, 0.04, 25),
            (float("-inf"), 0.0, 0),
        ],
        "roe": [
            (0.20, float("inf"), 100),
            (0.12, 0.20, 75),
            (0.05, 0.12, 50),
            (0.0, 0.05, 25),
            (float("-inf"), 0.0, 0),
        ],
        "capex_dep": [
            (1.2, 1.8, 100),
            (0.9, 1.2, 75),
            (1.8, 2.5, 75),
            (0.7, 0.9, 50),
            (2.5, 3.5, 50),
            (0.5, 0.7, 25),
            (3.5, float("inf"), 25),
            (float("-inf"), 0.5, 0),
        ],
        "current_ratio": [
            (2.0, float("inf"), 100),
            (1.5, 2.0, 75),
            (1.0, 1.5, 50),
            (0.7, 1.0, 25),
            (float("-inf"), 0.7, 0),
        ],
        "rollover_coverage": [
            (2.0, float("inf"), 100),
            (1.2, 2.0, 75),
            (0.8, 1.2, 50),
            (0.5, 0.8, 25),
            (float("-inf"), 0.5, 0),
        ],
        "altman_z": [
            (3.0, float("inf"), 100),
            (2.7, 3.0, 75),
            (1.8, 2.7, 50),
            (1.5, 1.8, 25),
            (float("-inf"), 1.5, 0),
        ],
    },

}


def load_config(excel_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from sn_rating_config.xlsx or explicit path,
    falling back to code defaults when sheets/values are missing.

   Excel only overrides defaults; missing/blank cells leave defaults in place.
    """
    cfg: Dict[str, Any] = {
        "SCORE_TO_RATING": list(DEFAULT_SCORE_TO_RATING),
        "RATING_SCALE": list(DEFAULT_RATING_SCALE),
        "RATING_WEIGHTS": dict(DEFAULT_RATING_WEIGHTS),
        "DISTRESS_BANDS": {k: list(v) for k, v in DEFAULT_DISTRESS_BANDS.items()},
        "MAX_DISTRESS_NOTCHES": DEFAULT_MAX_DISTRESS_NOTCHES,
        "QUAL_SCORE_SCALE": dict(DEFAULT_QUAL_SCORE_SCALE),
        "RATIOS_LOWER_BETTER": {
            fam: {name: list(bands) for name, bands in ratios.items()}
            for fam, ratios in DEFAULT_RATIOS_LOWER_BETTER.items()
        },
        "RATIOS_HIGHER_BETTER": {
            fam: {name: list(bands) for name, bands in ratios.items()}
            for fam, ratios in DEFAULT_RATIOS_HIGHER_BETTER.items()
        },
    }

    # Resolve Excel path
    if excel_path is None:
        excel_path = _input_path("sn_rating_config.xlsx")

    if not excel_path or not os.path.exists(excel_path):
        logger.info("No config Excel provided or file not found (%s), using code defaults.", excel_path)
        return cfg

    try:
        xldata = pd.read_excel(excel_path, sheet_name=None)
        logger.info("Loaded config overrides from %s", excel_path)

        # Case-insensitive sheet names
        sheets = {name.lower(): df for name, df in xldata.items()}

        # SCORE_TO_RATING + derived RATING_SCALE
        if "score_to_rating" in sheets:
            df = sheets["score_to_rating"].dropna(how="all")
            cols_lower = {c.lower(): c for c in df.columns}
            if {"threshold", "rating"}.issubset(cols_lower.keys()):
                thr_col = cols_lower["threshold"]
                rat_col = cols_lower["rating"]
                score_to_rating: List[Tuple[float, str]] = []
                for _, row in df.iterrows():
                    if pd.isna(row[thr_col]) or pd.isna(row[rat_col]):
                        continue
                    thr = float(row[thr_col])
                    rat = str(row[rat_col]).strip()
                    score_to_rating.append((thr, rat))
                if score_to_rating:
                    cfg["SCORE_TO_RATING"] = score_to_rating
                    cfg["RATING_SCALE"] = derive_rating_scale(score_to_rating)

        # QUAL_SCORE_SCALE
        if "qual_score_scale" in sheets:
            df = sheets["qual_score_scale"].dropna(how="all")
            cols_lower = {c.lower(): c for c in df.columns}
            if {"score", "boost_pct"}.issubset(cols_lower.keys()):
                s_col = cols_lower["score"]
                b_col = cols_lower["boost_pct"]
                qscale: Dict[int, float] = {}
                for _, row in df.iterrows():
                    if pd.isna(row[s_col]) or pd.isna(row[b_col]):
                        continue
                    s = int(row[s_col])
                    b = float(row[b_col])
                    qscale[s] = b
                if qscale:
                    cfg["QUAL_SCORE_SCALE"] = qscale

        # DISTRESS_BANDS
        if "distress_bands" in sheets:
            df = sheets["distress_bands"].dropna(how="all")
            cols_lower = {c.lower(): c for c in df.columns}
            if {"metric", "threshold", "notches_down"}.issubset(cols_lower.keys()):
                m_col = cols_lower["metric"]
                t_col = cols_lower["threshold"]
                n_col = cols_lower["notches_down"]
                bands: Dict[str, List[Tuple[float, int]]] = {}
                for _, row in df.iterrows():
                    if pd.isna(row[m_col]) or pd.isna(row[t_col]) or pd.isna(row[n_col]):
                        continue
                    metric = str(row[m_col]).strip()
                    thr = float(row[t_col])
                    nd = int(row[n_col])
                    bands.setdefault(metric, []).append((thr, nd))
                for m in bands:
                    bands[m].sort(key=lambda x: x[0])
                if bands:
                    cfg["DISTRESS_BANDS"] = bands

        # OTHERS: MAX_DISTRESS_NOTCHES + global weights
        if "others" in sheets:
            df = sheets["others"].dropna(how="all")
            cols_lower = {c.lower(): c for c in df.columns}
            if {"metric", "threshold"}.issubset(cols_lower.keys()):
                m_col = cols_lower["metric"]
                t_col = cols_lower["threshold"]
                for _, row in df.iterrows():
                    if pd.isna(row[m_col]) or pd.isna(row[t_col]):
                        continue
                    metric = str(row[m_col]).strip()
                    val = float(row[t_col])
                    if metric == "MAX_DISTRESS_NOTCHES":
                        cfg["MAX_DISTRESS_NOTCHES"] = int(val)
                    elif metric == "quantitative_weight":
                        cfg["RATING_WEIGHTS"]["quantitative"] = val
                    elif metric == "qualitative_weight":
                        cfg["RATING_WEIGHTS"]["qualitative"] = val

        # LOWER_BETTER overrides
        if "lower_better" in sheets:
            df = sheets["lower_better"].dropna(how="all")
            cols_lower = {c.lower(): c for c in df.columns}
            required = {"ratio_family", "ratio_name", "min_value", "max_value", "score"}
            if required.issubset(cols_lower.keys()):
                fam_col = cols_lower["ratio_family"]
                name_col = cols_lower["ratio_name"]
                lo_col = cols_lower["min_value"]
                hi_col = cols_lower["max_value"]
                s_col = cols_lower["score"]
                lb_overrides: Dict[str, Dict[str, List[Tuple[float, float, float]]]] = {}
                for _, row in df.iterrows():
                    if pd.isna(row[fam_col]) or pd.isna(row[name_col]) or pd.isna(row[lo_col]) or pd.isna(row[hi_col]) or pd.isna(row[s_col]):
                        continue
                    fam = str(row[fam_col]).strip().lower()
                    name = str(row[name_col]).strip().lower()
                    lo = float(row[lo_col])
                    hi = float(row[hi_col])
                    sc = float(row[s_col])
                    fam_dict = lb_overrides.setdefault(fam, {})
                    fam_dict.setdefault(name, []).append((lo, hi, sc))
                for fam, ratios in lb_overrides.items():
                    fam_dict = cfg["RATIOS_LOWER_BETTER"].setdefault(fam, {})
                    for name, bands in ratios.items():
                        fam_dict[name] = bands  # overwrite default only for that metric

        # HIGHER_BETTER overrides
        if "higher_better" in sheets:
            df = sheets["higher_better"].dropna(how="all")
            cols_lower = {c.lower(): c for c in df.columns}
            required = {"ratio_family", "ratio_name", "min_value", "max_value", "score"}
            if required.issubset(cols_lower.keys()):
                fam_col = cols_lower["ratio_family"]
                name_col = cols_lower["ratio_name"]
                lo_col = cols_lower["min_value"]
                hi_col = cols_lower["max_value"]
                s_col = cols_lower["score"]
                hb_overrides: Dict[str, Dict[str, List[Tuple[float, float, float]]]] = {}
                for _, row in df.iterrows():
                    if pd.isna(row[fam_col]) or pd.isna(row[name_col]) or pd.isna(row[lo_col]) or pd.isna(row[hi_col]) or pd.isna(row[s_col]):
                        continue
                    fam = str(row[fam_col]).strip().lower()
                    name = str(row[name_col]).strip().lower()
                    lo = float(row[lo_col])
                    hi = float(row[hi_col])
                    sc = float(row[s_col])
                    fam_dict = hb_overrides.setdefault(fam, {})
                    fam_dict.setdefault(name, []).append((lo, hi, sc))
                for fam, ratios in hb_overrides.items():
                    fam_dict = cfg["RATIOS_HIGHER_BETTER"].setdefault(fam, {})
                    for name, bands in ratios.items():
                        fam_dict[name] = bands

    except Exception as exc:
        logger.warning(
            "Failed to load config from Excel %s, using code defaults. %s",
            excel_path,
            exc,
        )

    return cfg