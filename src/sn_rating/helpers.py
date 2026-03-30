import math
import os
import sys
from statistics import mean
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd

from sn_rating.datamodel import RatioConfig, QualFactorConfig
from sn_rating.config import logger


def normalize_ratio_config(cfg: RatioConfig) -> RatioConfig:
    """Fill in default bucket/weight for a quantitative ratio config."""
    
    weight = cfg.weight if cfg.weight is not None else 1.0                     # Default weight=1.0
    bucket = cfg.bucket if cfg.bucket not in (None, "", " ") else "OTHERS"     # Fallback bucket
    return RatioConfig(                                                        # Return normalized copy
        code=cfg.code,
        name=cfg.name,
        bucket=bucket,
        weight=weight,
    )

def normalize_qual_config(cfg: QualFactorConfig) -> QualFactorConfig:
    """Fill in default bucket/weight for a qualitative factor config."""
    
    weight = cfg.weight if cfg.weight is not None else 1.0     # Default weight=1.0
    bucket = cfg.bucket if cfg.bucket not in (None, "", " ") else "OTHERS"
    return QualFactorConfig(
        code=cfg.code,
        name=cfg.name,
        bucket=bucket,
        weight=weight,
    )

def project_root() -> str:
    """
    Root directory where input/ and sn_rating/ live.

    - In dev: ...\SN-Rating-Model\src
    - In exe: folder containing run_sn_rating.exe
    """
    if getattr(sys, "frozen", False):
        # Running from PyInstaller exe
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        # Running from source; helpers.py is in sn_rating/
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def input_dir() -> str:
    """Ensure and return input/ folder under project root."""
    
    root = project_root()                                      # Base folder
    path = os.path.join(root, "input")                         # .../input
    os.makedirs(path, exist_ok=True)                           # Create if missing
    return path


def output_dir() -> str:
    """Ensure and return output/ folder under project root."""
    
    root = project_root()
    path = os.path.join(root, "output")
    os.makedirs(path, exist_ok=True)
    return path


def input_path(relative_name: str) -> str:
    """Return absolute path for a file in input/."""
    return os.path.join(project_root(), "input", relative_name)


def output_path(name: str) -> str:
    """Build full path to a file inside output/."""
    
    return os.path.join(output_dir(), name)


def resource_path(relative_path: str) -> str:
    """Locate resource relative to exe or package folder (for configs, templates, etc.)."""
    
    if getattr(sys, "frozen", False):                          # PyInstaller frozen mode
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))      # Module directory
    return os.path.join(base, relative_path)



class BandConfig:
    """
    Builds band lookups from config['RATIOS_LOWER_BETTER'] / ['RATIOS_HIGHER_BETTER'].
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.lower: Optional[pd.DataFrame] = None
        self.higher: Optional[pd.DataFrame] = None
        self.ratio_family: Dict[str, str] = {}
        self.direction: Dict[str, str] = {}
        self._load_from_config()

    def _build_df(
        self,
        ratio_dict: Dict[str, Dict[str, List[Tuple[float, float, float]]]],
        direction: str,
    ) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        for fam, ratios in ratio_dict.items():
            for name, bands in ratios.items():
                for lo, hi, score in bands:
                    rows.append(
                        {
                            "ratio_family": str(fam),
                            "ratio_name": str(name),
                            "min_value": float(lo),
                            "max_value": float(hi),
                            "score": float(score),
                            "__direction__": direction,
                        }
                    )
        return pd.DataFrame(rows) if rows else pd.DataFrame(
            columns=[
                "ratio_family",
                "ratio_name",
                "min_value",
                "max_value",
                "score",
                "__direction__",
            ]
        )

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in ["ratio_family", "ratio_name", "__direction__"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.lower()
        return df

    def _load_from_config(self) -> None:
        lb_dict = self.config.get("RATIOS_LOWER_BETTER", {})
        hb_dict = self.config.get("RATIOS_HIGHER_BETTER", {})

        lb_df = self._build_df(lb_dict, "lower")
        hb_df = self._build_df(hb_dict, "higher")

        if not lb_df.empty:
            lb_df = self._normalize(lb_df)
        if not hb_df.empty:
            hb_df = self._normalize(hb_df)

        self.lower = lb_df if not lb_df.empty else None
        self.higher = hb_df if not hb_df.empty else None

        all_frames: List[pd.DataFrame] = []
        if self.lower is not None:
            all_frames.append(self.lower)
        if self.higher is not None:
            all_frames.append(self.higher)
        if not all_frames:
            return

        all_bands_df = pd.concat(all_frames, ignore_index=True)

        for ratio_name, sub in all_bands_df.groupby("ratio_name"):
            fam = str(sub["ratio_family"].iloc[0])
            dirn = str(sub["__direction__"].iloc[0])
            self.ratio_family[ratio_name] = fam
            self.direction[ratio_name] = dirn

        logger.info("BandConfig: loaded families/directions for ratios: %s", self.ratio_family)

    def get_direction(self, metric: str) -> Optional[str]:
        m = str(metric).strip().lower()
        return self.direction.get(m)

    def lookup(self, metric: str, val: float) -> Optional[float]:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return None

        metric_norm = str(metric).strip().lower()
        dirn = self.get_direction(metric_norm)
        if dirn is None:
            return None

        df = self.lower if dirn == "lower" else self.higher
        if df is None or df.empty:
            return None

        dfm = df[df["ratio_name"] == metric_norm]
        if dfm.empty:
            return None

        for _, row in dfm.iterrows():
            lo, hi, s = row["min_value"], row["max_value"], row["score"]
            if lo <= val < hi:
                return float(s)

        lo_min = dfm["min_value"].min()
        hi_max = dfm["max_value"].max()
        if val < lo_min:
            row = dfm.loc[dfm["min_value"].idxmin()]
        else:
            row = dfm.loc[dfm["max_value"].idxmax()]
        return float(row["score"])


def classify_peer_with_bandconfig(
    metric_name: str,
    value: float,
    peer_avg: float,
    band_cfg,
    band: float = 0.10,
):
    """
    Direction-aware peer classification using BandConfig:
    - direction: 'higher' or 'lower' from band_cfg.get_direction(...)
    - band: +/- % around peer_avg that counts as 'on_par'
    """
    if (
        peer_avg is None or value is None
        or (isinstance(peer_avg, float) and math.isnan(peer_avg))
        or (isinstance(value, float) and math.isnan(value))
    ):
        return None, None, None, None

    dirn = band_cfg.get_direction(metric_name)   # "higher" / "lower" / None
    if dirn is None:
        dirn = "higher"                          # Default assume 'higher is better'

    lower = peer_avg * (1 - band)               # Lower bound for on_par zone
    upper = peer_avg * (1 + band)               # Upper bound for on_par zone

    if lower <= value <= upper:
        flag = "on_par"                          # Within ±band → on par with peers
    else:
        if dirn == "higher":                     # For higher-better metrics
            flag = "over" if value > upper else "under"
        else:                                    # For lower-better metrics (e.g. leverage)
            flag = "over" if value < lower else "under"

    return lower, upper, flag, peer_avg          # Return band bounds + classification


def score_qual_factor_numeric(
    value: int,
    qual_score_scale: Dict[int, float],
) -> Optional[float]:
    """
    Map 1–5 qualitative score to numeric via QUAL_SCORE_SCALE from config.
    Behavior identical to original, now without global.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return qual_score_scale.get(int(value))


def compute_altman_z_from_components(
    working_capital: float,
    total_assets: float,
    retained_earnings: float,
    ebit: float,
    market_value_equity: float,
    total_liabilities: float,
    sales: float,
) -> float:
    """Compute Altman Z-score from raw balance sheet/income statement components."""
    
    if total_assets == 0 or total_liabilities == 0:            # Avoid division by zero
        return float("nan")
    A = working_capital / total_assets
    B = retained_earnings / total_assets
    C = ebit / total_assets
    D = market_value_equity / total_liabilities
    E = sales / total_assets
    return 1.2 * A + 1.4 * B + 3.3 * C + 0.6 * D + 1.0 * E     # Standard Altman Z formula

def compute_peer_score(
    fin_current: Dict[str, float],
    peers: Dict[str, List[float]],
    band_cfg,   # BandConfig instance
    band: float = 0.10,
) -> Tuple[Optional[float], int, int, int, int]:
    """
    Compare issuer current ratios vs peer averages, return:
    (peer_score 0–100, underperform_count, outperform_count, on_par_count, total_compared).

    - direction comes from band_cfg.get_direction(rname): 'higher' or 'lower'
    - band: +/- % around peer_avg that counts as 'on_par'
    """

    under = 0
    over = 0
    on_par = 0
    total = 0

    for rname, peer_vals in peers.items():
        if rname not in fin_current or not peer_vals:
            continue

        cp = fin_current[rname]
        peer_avg = mean(peer_vals)
        if peer_avg == 0:
            continue

        total += 1

        # 10% band for "on_par"
        lower = peer_avg * (1 - band)
        upper = peer_avg * (1 + band)

        # Look up direction from BandConfig instead of guessing from the name
        dirn = band_cfg.get_direction(rname)   # "higher" / "lower" / None

        if dirn is None:
            # Safer: skip metrics with unknown direction
            # (or log a warning instead of silently assuming)
            total -= 1          # undo the increment; we are not comparing this one
            continue

        if lower <= cp <= upper:
            on_par += 1
        else:
            if dirn == "higher":
                # Higher is better
                if cp < lower:
                    under += 1
                elif cp > upper:
                    over += 1
            else:
                # Lower is better
                if cp > upper:
                    under += 1
                elif cp < lower:
                    over += 1

    if total == 0:
        return None, 0, 0, 0, 0

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

    return score, under, over, on_par, total


def score_to_rating(
    score: float,
    score_to_rating_table: List[Tuple[float, str]],
) -> str:
    """Map numeric score to rating using SCORE_TO_RATING from config."""
    for cutoff, grade in score_to_rating_table:  # high→low thresholds
        if score >= cutoff:
            return grade
    raise ValueError(f"Score {score} did not match any cutoff")


def safe_score_to_rating(
    score: float,
    score_to_rating_table: List[Tuple[float, str]],
) -> str:
    """Wrapper that logs errors and returns 'NR' if mapping fails."""
    try:
        return score_to_rating(score, score_to_rating_table)
    except ValueError as e:
        logger.error("Score-to-rating mapping failed: %s", e)
        return "NR"


def move_notches(
    grade: str,
    notches: int,
    rating_scale: List[str],
) -> str:
    """Move rating up/down by N notches within RATING_SCALE."""
    if grade not in rating_scale:
        return grade
    idx = rating_scale.index(grade)
    new_idx = max(0, min(idx - notches, len(rating_scale) - 1))
    return rating_scale[new_idx]
    

def apply_sovereign_cap(
    issuer_grade: str,
    sovereign_grade: Optional[str],
    rating_scale: List[str],
) -> str:
    """Apply sovereign rating cap: issuer cannot be stronger than sovereign."""
    if sovereign_grade is None:
        return issuer_grade
    if issuer_grade not in rating_scale or sovereign_grade not in rating_scale:
        return issuer_grade

    i = rating_scale.index(issuer_grade)
    s = rating_scale.index(sovereign_grade)
    return rating_scale[max(i, s)]


def compute_effective_weights(
    n_quant: int,
    n_qual: int,
    rating_weights: Dict[str, Optional[float]],
) -> Tuple[float, float]:
    """
    Compute final quant / qual weights.

    - If both set in rating_weights, normalize them so they sum to 1.0.
    - Otherwise, allocate by count of metrics (n_quant vs n_qual).
    - If both counts are zero, return (0.0, 0.0).
    """
    wq_cfg = rating_weights.get("quantitative")
    wl_cfg = rating_weights.get("qualitative")

    # Case 1: both explicitly configured → normalize
    if wq_cfg is not None and wl_cfg is not None:
        total = wq_cfg + wl_cfg
        if total > 0:
            wq = float(wq_cfg) / total
            wl = float(wl_cfg) / total
            return wq, wl
        # Degenerate case: both zero or negative → fall through to count-based
        # (or you could choose to return (0.0, 0.0) explicitly)

    # Case 2: at least one missing → derive from counts
    n_quant = max(n_quant, 0)
    n_qual = max(n_qual, 0)
    total = n_quant + n_qual
    if total == 0:
        return 0.0, 0.0

    wq = n_quant / total
    wl = n_qual / total
    return wq, wl
    

def get_rating_band(
    rating: str,
    score_to_rating_table: List[Tuple[float, str]],
) -> Tuple[float, float]:
    """Return (min_score, max_score) band for a given rating grade."""
    for i, (cutoff, grade) in enumerate(score_to_rating_table):
        if grade == rating:
            band_min = cutoff
            if i == 0:
                band_max = 100.0
            else:
                prev_cutoff, _ = score_to_rating_table[i - 1]
                band_max = prev_cutoff - 1.0
            return band_min, band_max
    raise ValueError(f"Unknown rating grade {rating!r}!")


def derive_outlook_band_only(
    combined_score: float,
    rating: str,
    score_to_rating_table: List[Tuple[float, str]],
) -> Tuple[str, str]:
    """Derive outlook (Positive/Stable/Negative) and band position based on rating band."""
    band_min, band_max = get_rating_band(rating, score_to_rating_table)
    cs = math.floor(combined_score)

    if cs >= band_max:
        outlook = "Positive"
    elif cs <= band_min:
        outlook = "Negative"
    else:
        outlook = "Stable"

    if cs <= band_min:
        band_position = "lower_band"
    elif cs >= band_max:
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
    """
    Adjust outlook using distress trend:
    - If distress_notches < 0 and metrics deteriorating → 'Negative'
    - Else → 'Stable' (or keep base_outlook if no distress).
    """
    
    if distress_notches >= 0:
        return base_outlook                                     # No negative distress → keep

    ratios = ["interest_coverage", "dscr", "altman_z"]          # Key distress metrics
    improving = False
    deteriorating = False

    for r in ratios:
        v0 = fin_t0.get(r)
        v1 = fin_t1.get(r)
        if v0 is None or v1 is None:
            continue
        if v0 > v1:
            improving = True                                    # Higher now than last year
        elif v0 < v1:
            deteriorating = True

    if deteriorating and not improving:
        return "Negative"
    return "Stable"


def rating_index(grade: str, rating_scale: List[str]) -> Optional[int]:
    """Return index of grade in RATING_SCALE, or None if unknown."""
    if grade not in rating_scale:
        return None
    return rating_scale.index(grade)


def is_stronger(r1: str, r2: str, rating_scale: List[str]) -> bool:
    """Return True if r1 is stronger (better rating) than r2."""
    i1 = rating_index(r1, rating_scale)
    i2 = rating_index(r2, rating_scale)
    if i1 is None or i2 is None:
        return False
    return i1 < i2


def is_weaker_or_equal(r1: str, r2: str, rating_scale: List[str]) -> bool:
    """Return True if r1 is weaker than or equal to r2."""
    i1 = rating_index(r1, rating_scale)
    i2 = rating_index(r2, rating_scale)
    if i1 is None or i2 is None:
        return False
    return i1 >= i2
    