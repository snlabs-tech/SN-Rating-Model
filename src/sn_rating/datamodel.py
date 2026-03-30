from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Quantitative inputs: 3-year financial time series + peer benchmarks
@dataclass
class QuantInputs:
    fin_t0: Dict[str, float]                           # Current year financial ratios
    fin_t1: Dict[str, float]                           # Prior year financial ratios  
    fin_t2: Dict[str, float]                           # Two years prior financial ratios
    components_t0: Dict[str, float]                    # Current year component scores
    components_t1: Dict[str, float]                    # Prior year component scores
    components_t2: Dict[str, float]                    # Two years prior component scores
    peers_t0: Dict[str, List[float]]                   # Peer group percentiles by ratio
    ratio_weights: Dict[str, float] = field(default_factory=dict)

# Qualitative inputs: Management/business risk factors (2-year history)
@dataclass
class QualInputs:
    factors_t0: Dict[str, int]                         # Current qualitative scores (1-5)
    factors_t1: Dict[str, int]                         # Prior year qualitative scores (1-5)


# Quantitative ratio configuration (weighting, bucketing for Excel UI)
@dataclass  
class RatioConfig:
    code: str                                         # e.g. "DEBT_EBITDA"
    name: str                                         # Human-readable name
    bucket: Optional[str] = None                      # "LEVERAGE", "PROFITABILITY", etc.
    weight: Optional[float] = None                    # User override (default 1.0)


# Qualitative factor configuration (bucketing for Excel UI)
@dataclass
class QualFactorConfig:
    code: str                                         # e.g. "MGMT_QUALITY"
    name: str                                         # Human-readable name  
    bucket: Optional[str] = None                      # "MANAGEMENT", "BUSINESS_RISK"
    weight: Optional[float] = None                    # User override (default 1.0)


# Complete rating outputs (Excel export + diagnostics)
@dataclass
class RatingOutputs:
    issuer_name: str                                  # Company name
    
    quantitative_score: float                         # Raw quant score (0-100)
    qualitative_score: float                          # Qual overlay score (0-100)  
    combined_score: float                             # Weighted final score (0-100)
    peer_score: Optional[float]                       # Percentile vs peers
    
    base_rating: str                                  # Score → rating (AAA, BB-, etc.)
    hardstop_rating: str                              # Distress threshold ceiling applied
    sovereign_rating: Optional[str]                   # Parent country rating
    capped_rating: str                                # Constrained rating
    final_rating: str                                 # Delivered rating
    
    hardstop_triggered: bool                          # Distressed rating thresholds breached or not
    hardstop_details: Dict[str, float]                # Details of the distressed ratio and the notches down
    distress_notches: int                             # Down notches from distress (-4 to 0)
    sovereign_cap_binding: bool                       # Rating actually constrained due to the sovereign rating?
    sovereign_outlook: Optional[str]                  # Parent country rating outlook
    outlook: str                                      # Final outlook (Stable, Negative)
    bucket_avgs: Dict[str, float]                     # Avg by bucket (Leverage=72.3)
    
    altman_z_t0: float                                # Bankruptcy score
    flags: Dict[str, bool]                            # Distress flags triggered
    
    rating_explanation: str                           # Human-readable methodology
    peer_underperform_count: int                      # # peers beaten
    peer_outperform_count: int                        # # peers worse  
    peer_on_par_count: int                            # # within +/-10% of peer avg
    peer_total_compared: int                          # Total peers benchmarked
    
    band_position: str                                # "Top quartile", "Distressed"
    
    ratio_log: List[Dict[str, object]]                # All ratio calculations
    qual_log: List[Dict[str, object]]                 # All qual calculations
    
    base_outlook: str                                 # Pre-adjustment outlook
    hardstop_outlook: str                             # Sovereign-adjusted outlook  
    final_outlook: str                                # Delivered outlook
    
    n_quant: int                                      # # quantitative ratios used
    n_qual: int                                       # # qualitative factors used
    wq: float                                         # Final quant weight
    wl: float                                         # Final qual weight