import math
import os
import sys
from statistics import mean
from typing import Dict, List, Optional, Tuple

import pandas as pd

from sn_rating.datamodel import RatioConfig, QualFactorConfig
from sn_rating.config import (
    SCORE_TO_RATING,
    RATING_SCALE,
    RATING_WEIGHTS,
    DISTRESS_BANDS,
    MAX_DISTRESS_NOTCHES,
    QUAL_SCORE_SCALE,
    logger,
)


def normalize_ratio_config(cfg: RatioConfig) -> RatioConfig:
    weight = cfg.weight if cfg.weight is not None else 1.0
    bucket = cfg.bucket if cfg.bucket not in (None, "", " ") else "OTHERS"
    return RatioConfig(
        code=cfg.code,
        name=cfg.name,
        bucket=bucket,
        weight=weight,
    )


def normalize_qual_config(cfg: QualFactorConfig) -> QualFactorConfig:
    weight = cfg.weight if cfg.weight is not None else 1.0
    bucket = cfg.bucket if cfg.bucket not in (None, "", " ") else "OTHERS"
    return QualFactorConfig(
        code=cfg.code,
        name=cfg.name,
        bucket=bucket,
        weight=weight,
    )


def project_root() -> str:
    # Folder where run_sn_rating.exe / run_sn_rating.bat live (one level above sn_rating)
    if hasattr(sys, "frozen"):  # running as PyInstaller EXE
        base = os.path.dirname(sys.executable)
    else:  # running as plain Python
        base = os.path.dirname(os.path.abspath(__file__))
        base = os.path.dirname(base)  # go up from sn_rating/ to project root
    return base


def input_dir() -> str:
    root = project_root()
    path = os.path.join(root, "input")
    os.makedirs(path, exist_ok=True)
    return path


def output_dir() -> str:
    root = project_root()
    path = os.path.join(root, "output")
    os.makedirs(path, exist_ok=True)
    return path


def input_path(name: str) -> str:
    return os.path.join(input_dir(), name)


def output_path(name: str) -> str:
    return os.path.join(output_dir(), name)


def resource_path(relative_path: str) -> str:
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


class BandConfig:
    """
    Reads sn_rating_config.xlsx and infers for each ratio_name:
    - ratio_family (cluster) from the band rows
    - direction: 'lower' or 'higher' depending on which sheet it appears in
    """

    def __init__(self, config_path: str = "sn_rating_config.xlsx"):
        # Always resolve via input_path so exe uses its own folder
        self.config_path = input_path(config_path)
        self.lower: Optional[pd.DataFrame] = None
        self.higher: Optional[pd.DataFrame] = None
        self.ratio_family: Dict[str, str] = {}
        self.direction: Dict[str, str] = {}
        self._load()

    def _norm_cols(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [str(c).strip().lower() for c in df.columns]
        for c in ["ratio_family", "ratio_name"]:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip().str.lower()
        return df

    def _load(self):
        with pd.ExcelFile(self.config_path) as xls:
            lb = pd.read_excel(xls, "lower_better")
            hb = pd.read_excel(xls, "higher_better")
        self.lower = self._norm_cols(lb)
        self.higher = self._norm_cols(hb)

        all_bands = []
        if self.lower is not None:
            tmp = self.lower.copy()
            tmp["__direction__"] = "lower"
            all_bands.append(tmp)
        if self.higher is not None:
            tmp = self.higher.copy()
            tmp["__direction__"] = "higher"
            all_bands.append(tmp)
        if not all_bands:
            return

        all_bands_df = pd.concat(all_bands, ignore_index=True)

        for ratio_name, sub in all_bands_df.groupby("ratio_name"):
            fam = str(sub["ratio_family"].iloc[0])
            dirn = str(sub["__direction__"].iloc[0])
            self.ratio_family[ratio_name] = fam
            self.direction[ratio_name] = dirn

        logger.info(
            "BandConfig: loaded families/directions for ratios: %s",
            self.ratio_family,
        )

    def get_direction(self, metric: str) -> Optional[str]:
        m = metric.strip().lower()
        return self.direction.get(m)

    def lookup(self, metric: str, val: float) -> Optional[float]:
        metric = metric.strip().lower()
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return None

        dirn = self.get_direction(metric)
        if dirn is None:
            return None

        df = self.lower if dirn == "lower" else self.higher
        if df is None:
            return None

        dfm = df[df["ratio_name"] == metric]
        if dfm.empty:
            return None

        # First try to find a band where min_value <= val < max_value
        for _, row in dfm.iterrows():
            lo, hi = row["min_value"], row["max_value"]
            s = row["score"]
            if lo <= val < hi:
                return float(s)

        # If outside configured bands, clamp to lowest or highest band
        lo_min = dfm["min_value"].min()
        hi_max = dfm["max_value"].max()
        if val < lo_min:
            row = dfm.loc[dfm["min_value"].idxmin()]
        else:
            row = dfm.loc[dfm["max_value"].idxmax()]
        return float(row["score"])


def score_qual_factor_numeric(value: int) -> Optional[float]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return QUAL_SCORE_SCALE.get(int(value))


def compute_altman_z_from_components(
    working_capital: float,
    total_assets: float,
    retained_earnings: float,
    ebit: float,
    market_value_equity: float,
    total_liabilities: float,
    sales: float,
) -> float:
    if total_assets == 0 or total_liabilities == 0:
        return float("nan")
    A = working_capital / total_assets
    B = retained_earnings / total_assets
    C = ebit / total_assets
    D = market_value_equity / total_liabilities
    E = sales / total_assets
    return 1.2 * A + 1.4 * B + 3.3 * C + 0.6 * D + 1.0 * E


def compute_peer_score(
    fin_current: Dict[str, float],
    peers: Dict[str, List[float]],
) -> Tuple[Optional[float], int, int, int]:
    under = 0
    over = 0
    total = 0

    for rname, peer_vals in peers.items():
        if rname not in fin_current or not peer_vals:
            continue

        cp = fin_current[rname]
        peer_avg = mean(peer_vals)
        if peer_avg == 0:
            continue

        total += 1

        if "debt" in rname or "leverage" in rname:
            if cp > peer_avg * 1.10:
                under += 1
            elif cp < peer_avg * 0.90:
                over += 1
        else:
            if cp < peer_avg * 0.90:
                under += 1
            elif cp > peer_avg * 1.10:
                over += 1

    if total == 0:
        return None, 0, 0, 0

    under_share = under / total

    if under_share <= 0.10:
        score = 100.0
    elif under_share <= 0.30:
        score = 75.0
    elif under_share <= 0.60:
        score = 50.0
    elif under_share <= 0.80:
        score = 25.0
    else:
        score = 0.0

    return score, under, over, total


def score_to_rating(score: float) -> str:
    for cutoff, grade in SCORE_TO_RATING:
        if score >= cutoff:
            return grade
    raise ValueError(f"Score {score} did not match any cutoff")


def safe_score_to_rating(score: float) -> str:
    try:
        return score_to_rating(score)
    except ValueError as e:
        logger.error("Score-to-rating mapping failed: %s", e)
        return "N/R"


def move_notches(grade: str, notches: int) -> str:
    if grade not in RATING_SCALE:
        return grade
    idx = RATING_SCALE.index(grade)
    new_idx = max(0, min(idx - notches, len(RATING_SCALE) - 1))
    return RATING_SCALE[new_idx]


def apply_sovereign_cap(
    issuer_grade: str,
    sovereign_grade: Optional[str],
) -> str:
    if sovereign_grade is None:
        return issuer_grade
    if issuer_grade not in RATING_SCALE or sovereign_grade not in RATING_SCALE:
        return issuer_grade
    i = RATING_SCALE.index(issuer_grade)
    s = RATING_SCALE.index(sovereign_grade)
    return RATING_SCALE[max(i, s)]


def compute_effective_weights(n_quant: int, n_qual: int) -> Tuple[float, float]:
    wq_cfg = RATING_WEIGHTS["quantitative"]
    wl_cfg = RATING_WEIGHTS["qualitative"]

    if wq_cfg is not None and wl_cfg is not None:
        return float(wq_cfg), float(wl_cfg)

    n_quant = max(n_quant, 0)
    n_qual = max(n_qual, 0)
    total = n_quant + n_qual

    if total == 0:
        return 0.0, 0.0

    wq = n_quant / total
    wl = n_qual / total
    return wq, wl


def get_rating_band(rating: str) -> Tuple[float, float]:
    for i, (cutoff, grade) in enumerate(SCORE_TO_RATING):
        if grade == rating:
            band_min = cutoff
            if i == 0:
                band_max = 100.0
            else:
                prev_cutoff, _ = SCORE_TO_RATING[i - 1]
                band_max = prev_cutoff - 1.0
            return band_min, band_max
    raise ValueError(f"Unknown rating grade: {rating!r}")


def derive_outlook_band_only(combined_score: float, rating: str) -> Tuple[str, str]:
    band_min, band_max = get_rating_band(rating)
    cs = math.floor(combined_score)

    if cs == band_max:
        outlook = "Positive"
    elif cs == band_min:
        outlook = "Negative"
    else:
        outlook = "Stable"

    if cs == band_min:
        band_position = "lower_band"
    elif cs == band_max:
        band_position = "upper_band"
    else:
        band_position = "middle_band"

    return outlook, band_position


def derive_outlook_with_distress_trend(
    base_outlook: str,
    distress_notches: int,
    fin_t0: dict[str, float],
    fin_t1: dict[str, float],
) -> str:
    if distress_notches >= 0:
        return base_outlook

    ratios = ["interest_coverage", "dscr", "altman_z"]
    improving = False
    deteriorating = False

    for r in ratios:
        v0 = fin_t0.get(r)
        v1 = fin_t1.get(r)
        if v0 is None or v1 is None:
            continue
        if v0 > v1:
            improving = True
        elif v0 < v1:
            deteriorating = True

    if deteriorating and not improving:
        return "Negative"
    return "Stable"


def rating_index(grade: str) -> Optional[int]:
    if grade not in RATING_SCALE:
        return None
    return RATING_SCALE.index(grade)


def is_stronger(r1: str, r2: str) -> bool:
    i1 = rating_index(r1)
    i2 = rating_index(r2)
    if i1 is None or i2 is None:
        return False
    return i1 < i2


def is_weaker_or_equal(r1: str, r2: str) -> bool:
    i1 = rating_index(r1)
    i2 = rating_index(r2)
    if i1 is None or i2 is None:
        return False
    return i1 >= i2
