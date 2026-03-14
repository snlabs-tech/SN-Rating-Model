from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class QuantInputs:
    fin_t0: Dict[str, float]
    fin_t1: Dict[str, float]
    fin_t2: Dict[str, float]
    components_t0: Dict[str, float]
    components_t1: Dict[str, float]
    components_t2: Dict[str, float]
    peers_t0: Dict[str, List[float]]


@dataclass
class QualInputs:
    factors_t0: Dict[str, int]
    factors_t1: Dict[str, int]


@dataclass
class RatioConfig:
    code: str
    name: str
    bucket: Optional[str] = None     # e.g. "LEVERAGE", "PROFITABILITY"
    weight: Optional[float] = None   # user-defined importance, default 1.0


@dataclass
class QualFactorConfig:
    code: str
    name: str
    bucket: Optional[str] = None     # e.g. "MANAGEMENT", "BUSINESS_RISK"
    weight: Optional[float] = None   # default 1.0


@dataclass
class RatingOutputs:
    issuer_name: str
    quantitative_score: float
    qualitative_score: float
    combined_score: float
    peer_score: Optional[float]
    base_rating: str
    distress_notches: int
    hardstop_rating: str
    capped_rating: str
    final_rating: str
    hardstop_triggered: bool
    hardstop_details: Dict[str, float]
    sovereign_rating: Optional[str]
    sovereign_outlook: Optional[str]
    sovereign_cap_binding: bool
    outlook: str
    bucket_avgs: Dict[str, float]
    altman_z_t0: float
    flags: Dict[str, bool]
    rating_explanation: str
    peer_underperform_count: int
    peer_outperform_count: int
    peer_total_compared: int
    band_position: str
    ratio_log: List[Dict[str, object]]
    qual_log: List[Dict[str, object]]
    base_outlook: str
    hardstop_outlook: str
    final_outlook: str
    n_quant: int
    n_qual: int
    wq: float
    wl: float
