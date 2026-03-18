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
    Reads sn_rating_config.xlsx and infers, for each ratio_name:
    - ratio_family (cluster) from the band rows
    - direction: 'lower' or 'higher' depending on which sheet it appears in
    """

    def __init__(self, config_path: str = "sn_rating_config.xlsx"):
        # Always resolve via input_path so exe uses its own folder
        self.config_path = input_path(config_path)             # Input config Excel path
        self.lower: Optional[pd.DataFrame] = None              # Bands where lower is better
        self.higher: Optional[pd.DataFrame] = None             # Bands where higher is better
        self.ratio_family: Dict[str, str] = {}                 # "ratio_name" → "family"
        self.direction: Dict[str, str] = {}                    # "ratio_name" → "lower"/"higher"
        self._load()                                           # Load immediately on init

    def _norm_cols(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column and key text to lowercase/stripped for robust matching."""
        
        df = df.copy()
        df.columns = [str(c).strip().lower() for c in df.columns]  # Standardize headers
        for c in ["ratio_family", "ratio_name"]:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip().str.lower()  # Normalize keys
        return df

    def _load(self) -> None:
        """Read Excel bands, split into lower_better/higher_better, build indexes."""
        
        with pd.ExcelFile(self.config_path) as xls:            # Open config workbook
            lb = pd.read_excel(xls, "lower_better")            # Bands: lower values are better
            hb = pd.read_excel(xls, "higher_better")           # Bands: higher values are better
        self.lower = self._norm_cols(lb)                       # Normalize text
        self.higher = self._norm_cols(hb)

        all_bands = []                                         # Collect both directions
        if self.lower is not None:
            tmp = self.lower.copy()
            tmp["__direction__"] = "lower"                     # Mark rows from lower sheet
            all_bands.append(tmp)
        if self.higher is not None:
            tmp = self.higher.copy()
            tmp["__direction__"] = "higher"                    # Mark rows from higher sheet
            all_bands.append(tmp)
        if not all_bands:                                      # Nothing loaded → bail
            return

        all_bands_df = pd.concat(all_bands, ignore_index=True) # Unified table of all bands

        for ratio_name, sub in all_bands_df.groupby("ratio_name"):  # For each metric
            fam = str(sub["ratio_family"].iloc[0])             # First family's name
            dirn = str(sub["__direction__"].iloc[0])           # "lower" or "higher"
            self.ratio_family[ratio_name] = fam
            self.direction[ratio_name] = dirn

        logger.info(                                           # Log summary for debugging
            "BandConfig: loaded families/directions for ratios: %s",
            self.ratio_family,
        )

    def get_direction(self, metric: str) -> Optional[str]:
        """Return 'lower' or 'higher' for a given ratio metric, if known."""
        
        m = metric.strip().lower()                             # Normalize lookup key
        return self.direction.get(m)

    def lookup(self, metric: str, val: float) -> Optional[float]:
        """Lookup band score for a metric/value using configured bands."""
        
        metric = metric.strip().lower()
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return None                                        # No score for missing value

        dirn = self.get_direction(metric)                      # "lower"/"higher"/None
        if dirn is None:
            return None

        df = self.lower if dirn == "lower" else self.higher    # Pick proper band table
        if df is None:
            return None

        dfm = df[df["ratio_name"] == metric]                   # Filter rows for this metric
        if dfm.empty:
            return None

        # First try to find a band where min_value <= val < max_value
        for _, row in dfm.iterrows():
            lo, hi = row["min_value"], row["max_value"]
            s = row["score"]
            if lo <= val < hi:
                return float(s)                                # Found matching band

        # If outside configured bands, clamp to lowest or highest band
        lo_min = dfm["min_value"].min()
        hi_max = dfm["max_value"].max()
        if val < lo_min:
            row = dfm.loc[dfm["min_value"].idxmin()]           # Use lowest band
        else:
            row = dfm.loc[dfm["max_value"].idxmax()]           # Use highest band
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


def score_qual_factor_numeric(value: int) -> Optional[float]:
    """Map 1–5 qualitative score to numeric via QUAL_SCORE_SCALE."""
    
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


def score_to_rating(score: float) -> str:
    """Map numeric score to rating using SCORE_TO_RATING cutoffs."""
    
    for cutoff, grade in SCORE_TO_RATING:                      # Iterate high→low thresholds
        if score >= cutoff:
            return grade
    raise ValueError(f"Score {score} did not match any cutoff") # only a backstop although the scenario is rare


def safe_score_to_rating(score: float) -> str:
    """Wrapper that logs errors and returns 'N/R' if mapping fails."""
    
    try:
        return score_to_rating(score)
    except ValueError as e:
        logger.error("Score-to-rating mapping failed: %s", e)
        return "N/R"


def move_notches(grade: str, notches: int) -> str:
    """Move rating up/down by N notches within RATING_SCALE."""
    
    if grade not in RATING_SCALE:
        return grade                                           # Unknown grade → unchanged
    idx = RATING_SCALE.index(grade)                            # Current position
    new_idx = max(0, min(idx - notches, len(RATING_SCALE) - 1))# Subtract notches, clamp to bounds (ensures it is not below 0 or above the last index)
    return RATING_SCALE[new_idx]


def apply_sovereign_cap(
    issuer_grade: str,
    sovereign_grade: Optional[str],
) -> str:
    """Apply sovereign rating cap: issuer cannot be stronger than sovereign."""
    
    if sovereign_grade is None:
        return issuer_grade
    if issuer_grade not in RATING_SCALE or sovereign_grade not in RATING_SCALE:
        return issuer_grade
    i = RATING_SCALE.index(issuer_grade)
    s = RATING_SCALE.index(sovereign_grade)
    return RATING_SCALE[max(i, s)]                             # Weaker of the two (higher index)



def compute_effective_weights(n_quant: int, n_qual: int) -> Tuple[float, float]:
    """
    Compute final quant / qual weights:
    - If both set in RATING_WEIGHTS: use them.
    - Otherwise, allocate by count of metrics (n_quant vs n_qual).
    """
    
    wq_cfg = RATING_WEIGHTS["quantitative"]
    wl_cfg = RATING_WEIGHTS["qualitative"]

    if wq_cfg is not None and wl_cfg is not None:              # Explicit config from Excel
        return float(wq_cfg), float(wl_cfg)

    n_quant = max(n_quant, 0)
    n_qual = max(n_qual, 0)
    total = n_quant + n_qual

    if total == 0:
        return 0.0, 0.0                                        # No metrics at all

    wq = n_quant / total                                       # Proportional weight
    wl = n_qual / total
    return wq, wl


def get_rating_band(rating: str) -> Tuple[float, float]:
    """Return [min_score, max_score] band for a given rating grade."""
    
    for i, (cutoff, grade) in enumerate(SCORE_TO_RATING):
        if grade == rating:
            band_min = cutoff                                  # Lower bound = its own cutoff
            if i == 0:
                band_max = 100.0                               # Top rating extends to 100
            else:
                prev_cutoff, _ = SCORE_TO_RATING[i - 1]        # Next better rating's cutoff
                band_max = prev_cutoff - 1.0                   # One point below that
            return band_min, band_max
    raise ValueError(f"Unknown rating grade: {rating!r}")



def derive_outlook_band_only(combined_score: float, rating: str) -> Tuple[str, str]:
    """
    Derive outlook ('Positive', 'Stable', 'Negative') and band position
    based only on where combined_score sits within the rating band.
    """
    
    band_min, band_max = get_rating_band(rating)
    cs = math.floor(combined_score)                            # Discrete score for logic

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


def rating_index(grade: str) -> Optional[int]:
    """Return index of grade in RATING_SCALE, or None if unknown."""
    
    if grade not in RATING_SCALE:
        return None
    return RATING_SCALE.index(grade)


def is_stronger(r1: str, r2: str) -> bool:
    """Return True if r1 is stronger (better rating) than r2."""
    
    i1 = rating_index(r1)
    i2 = rating_index(r2)
    if i1 is None or i2 is None:
        return False
    return i1 < i2                                             # Lower index = stronger


def is_weaker_or_equal(r1: str, r2: str) -> bool:
    """Return True if r1 is weaker than or equal to r2."""
    
    i1 = rating_index(r1)
    i2 = rating_index(r2)
    if i1 is None or i2 is None:
        return False
    return i1 >= i2                                            # Higher index = weaker/equal
