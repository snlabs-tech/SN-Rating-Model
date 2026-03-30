# sn_rating/model.py

import math
from typing import Dict, List, Optional, Tuple, Any

from .config import load_config, logger
from .datamodel import QuantInputs, QualInputs, RatingOutputs
from .helpers import (
    BandConfig,
    compute_altman_z_from_components,
    compute_effective_weights,
    compute_peer_score,
    derive_outlook_band_only,
    derive_outlook_with_distress_trend,
    move_notches,
    safe_score_to_rating,
    score_qual_factor_numeric,
    apply_sovereign_cap,
    rating_index,
    is_stronger,
    is_weaker_or_equal,
    classify_peer_with_bandconfig,
)

class RatingModel:
    """Main engine: compute full rating from quantitative & qualitative inputs."""

    def __init__(
        self,
        cp_name: str,
        bands: BandConfig,
        config_excel_path: Optional[str] = None,
    ):
        self.cp_name = cp_name
        self.bands = bands
        self.config: Dict[str, Any] = load_config(config_excel_path)
        

    def _ensure_altman_z(self, fin: Dict[str, float], comps: Dict[str, float]) -> Optional[float]:
        """Ensure fin['altman_z'] exists; compute from components if possible."""
        
        # 1. If already present and finite, just return it
        z_existing = fin.get("altman_z")
        if z_existing is not None:
            try:
                if not math.isnan(z_existing):
                    return z_existing
            except TypeError:
                return z_existing  # Non-float but present → trust it
        
        # 2. Safely extract components
        wc   = comps.get("working_capital")
        ta   = comps.get("total_assets")
        re   = comps.get("retained_earnings")
        ebit = comps.get("ebit")
        mve  = comps.get("market_value_equity")
        tl   = comps.get("total_liabilities")
        sales = comps.get("sales")
        
        # 3. If anything essential is missing or zero, skip Altman
        if None in (wc, ta, re, ebit, mve, tl, sales) or ta == 0 or tl == 0:
            logger.info("%s-Altman_Z: skipped (missing/invalid components)", self.cp_name)
            return None
        
        # 4. Compute Z from valid components
        z = compute_altman_z_from_components(wc, ta, re, ebit, mve, tl, sales)
        fin["altman_z"] = z
        logger.info("%s-AltmanZ: computed z=%.3f from components", self.cp_name, z)
        return z


    # --------- QUANTITATIVE BLOCK ---------

    def compute_quantitative(
        self,
        q: QuantInputs,
        ratio_weights: Dict[str, float],
        enable_peer_positioning: bool,
        fin: Dict[str, float],
    ) -> Tuple[
        float,                    # quantitative_score
        Optional[float],          # peer_score
        Dict[str, float],         # bucket_avgs
        int,                      # n_quant_items
        int,                      # peer_under
        int,                      # peer_over
        int,                      # peer_on_par
        int,                      # peer_total
        List[Dict[str, object]],  # ratio_log
    ]:

        total_weighted = 0.0                              # Σ (weight * score)
        total_weight = 0.0                                # Σ weight
        bucket_weighted: Dict[str, float] = {}           # Per-bucket Σ(weight * score)
        bucket_weight: Dict[str, float] = {}             # Per-bucket Σ(weight)
        ratio_log: List[Dict[str, object]] = []          # Detailed per-ratio log
        n_quant_items = 0                                 # Count of quant metrics used

        # Per-ratio scoring
        for rname, val in fin.items():
            if self.bands.get_direction(rname) is None:  # Skip ratios not configured in bands
                continue

            score = self.bands.lookup(rname, val)        # Map value → 0-100 band score
            if score is None:
                logger.info("%s-Quant: no band/score for ratio %s", self.cp_name, rname)
                continue

            w = float(ratio_weights.get(rname, 1.0))     # Default weight=1.0 if not provided
            n_quant_items += 1

            fam = self.bands.ratio_family.get(rname.strip().lower(), "OTHERS")  # Bucket

            total_weighted += w * score                  # Aggregate totals
            total_weight += w

            bucket_weighted[fam] = bucket_weighted.get(fam, 0.0) + w * score
            bucket_weight[fam] = bucket_weight.get(fam, 0.0) + w

            logger.info(
                "%s-Quant: %s value=%.2f score=%.1f weight=%.1f family=%s",
                self.cp_name,
                rname,
                val,
                score,
                w,
                fam,
            )

            # Per-ratio peer positioning with ±10% band, direction-aware
            peer_flag = None      # under, over, on_par
            peer_avg = None
            lower_bound = None
            upper_bound = None

            if enable_peer_positioning and q.peers_t0:
                peer_vals = q.peers_t0.get(rname)
                if peer_vals:
                    try:
                        vals = [v for v in peer_vals if v is not None]
                        peer_avg = sum(vals) / len(vals) if vals else None
                    except TypeError:
                        peer_avg = None

                    if peer_avg is not None and peer_avg != 0:
                        lower_bound, upper_bound, peer_flag, peer_avg = classify_peer_with_bandconfig(
                            rname,
                            val,
                            peer_avg,
                            self.bands,
                            band=0.10,  # ±10% on-par band
                        )

            ratio_log.append(
                {
                    "Name": rname,
                    "Value": val,
                    "Score": score,
                    "Weight": w,
                    "Bucket": fam,
                    "PeerFlag": peer_flag,
                    "PeerAvg": peer_avg,
                    "PeerLowerBound": lower_bound,
                    "PeerUpperBound": upper_bound,
                    # "DistressNotches" added later
                }
            )

        # Aggregate peer score (overall peer positioning)
        peer_score: Optional[float] = None
        peer_under = peer_over = peer_on_par = peer_total = 0

        if enable_peer_positioning and q.peers_t0:
            (
                peer_score,
                peer_under,
                peer_over,
                peer_on_par,
                peer_total,
            ) = compute_peer_score(fin, q.peers_t0, self.bands, band=0.10)
                
            if peer_score is not None:
                w_peer = 1.0           #weight of the peer‑positioning component within the quantitative score block
                n_quant_items += 1
        
                total_weighted += w_peer * peer_score
                total_weight += w_peer
        
                bucket_weighted["peer"] = bucket_weighted.get("peer", 0.0) + w_peer * peer_score
                bucket_weight["peer"] = bucket_weight.get("peer", 0.0) + w_peer
        
                logger.info(
                    "%s-PeerPositioning: score=%.1f under=%d over=%d on_par=%d total=%d",
                    self.cp_name,
                    peer_score,
                    peer_under,
                    peer_over,
                    peer_on_par,
                    peer_total,
                )
         
        else:
            peer_score = None
            peer_under = peer_over = peer_on_par = peer_total = 0


        quantitative_score = total_weighted / total_weight if total_weight > 0 else 0.0
        logger.info("%s-Quant: aggregate weighted score=%.1f", self.cp_name, quantitative_score)

        bucket_avgs = {
            b: round(bucket_weighted[b] / bucket_weight[b], 1)
            for b in bucket_weight
            if bucket_weight[b] > 0
        }

        return (
            quantitative_score,
            peer_score,
            bucket_avgs,
            n_quant_items,
            peer_under,
            peer_over,
            peer_on_par,
            peer_total,
            ratio_log,
        )

    # --------- QUALITATIVE BLOCK ---------
    
    def compute_qualitative(
        self,
        ql: QualInputs,
        qual_weights: Dict[str, float],
        qual_buckets: Dict[str, str],
    ) -> Tuple[float, int, List[Dict[str, object]]]:
        """Compute weighted qualitative score and log."""
        total_weighted = 0.0
        total_weight = 0.0
        n_qual_items = 0
        qual_log: List[Dict[str, object]] = []

        qual_scale = self.config["QUAL_SCORE_SCALE"]

        for name, val in ql.factors_t0.items():
            # Skip missing / NaN values
            if val is None or (isinstance(val, float) and math.isnan(val)):
                logger.info(
                    "%s-Qual: factor %s has NaN/None value, skipping",
                    self.cp_name,
                    name,
                )
                continue

            s = score_qual_factor_numeric(val, qual_scale)
            if s is None:
                logger.info(
                    "%s-Qual: unknown or out-of-range factor %s=%s",
                    self.cp_name,
                    name,
                    val,
                )
                continue

            w = float(qual_weights.get(name, 1.0))
            bucket = qual_buckets.get(name, "OTHERS")

            total_weighted += w * s
            total_weight += w
            n_qual_items += 1

            logger.info(
                "%s-Qual: %s=%s score=%.1f weight=%.1f bucket=%s",
                self.cp_name,
                name,
                val,
                s,
                w,
                bucket,
            )
            qual_log.append(
                {"Name": name, "Value": val, "Score": s, "Weight": w, "Bucket": bucket}
            )

        qualitative_score = total_weighted / total_weight if total_weight > 0 else 0.0
        logger.info(
            "%s-Qual: aggregate weighted score=%.1f",
            self.cp_name,
            qualitative_score,
        )
        return qualitative_score, n_qual_items, qual_log

    # --------- DISTRESS / HARDSTOPS ---------

    def compute_distress_notches(
        self,
        fin: Dict[str, float],
    ) -> Tuple[int, Dict[str, float], Dict[str, int]]:
        """Compute total distress notches and per-metric details."""
        distress_bands = self.config["DISTRESS_BANDS"]
        max_notches = self.config["MAX_DISTRESS_NOTCHES"]

        total_notches = 0
        details: Dict[str, float] = {}
        per_metric_notches: Dict[str, int] = {}

        ic = fin.get("interest_coverage")
        if ic is not None:
            for threshold, notches in distress_bands.get("interest_coverage", []):
                if ic <= threshold:
                    total_notches += notches
                    details["interest_coverage"] = ic
                    per_metric_notches["interest_coverage"] = notches
                    break

        dscr = fin.get("dscr")
        if dscr is not None:
            for threshold, notches in distress_bands.get("dscr", []):
                if dscr <= threshold:
                    total_notches += notches
                    details["dscr"] = dscr
                    per_metric_notches["dscr"] = notches
                    break

        altman_z = fin.get("altman_z")
        if altman_z is not None:
            for threshold, notches in distress_bands.get("altman_z", []):
                if altman_z <= threshold:
                    total_notches += notches
                    details["altman_z"] = altman_z
                    per_metric_notches["altman_z"] = notches
                    break

        if total_notches < max_notches:
            total_notches = max_notches

        return total_notches, details, per_metric_notches

    # --------- TOP-LEVEL ORCHESTRATION ---------

    def compute_final_rating(
        self,
        quant_inputs: QuantInputs,
        qual_inputs: QualInputs,
        sovereign_rating: Optional[str] = None,
        sovereign_outlook: Optional[str] = None,
        enable_hardstops: bool = False,
        enable_sovereign_cap: bool = False,
        enable_peer_positioning: bool = False,
        ratio_weights: Optional[Dict[str, float]] = None,
        qual_weights: Optional[Dict[str, float]] = None,
        qual_buckets: Optional[Dict[str, str]] = None,
    ) -> RatingOutputs:
        """Main API: returns fully populated RatingOutputs dataclass."""
        ratio_weights = ratio_weights or {}
        qual_weights = qual_weights or {}
        qual_buckets = qual_buckets or {}

        fin = dict(quant_inputs.fin_t0)
        _ = self._ensure_altman_z(fin, quant_inputs.components_t0)

        (
            quant_score,
            peer_score,
            bucket_avgs,
            n_quant,
            peer_under,
            peer_over,
            peer_on_par,
            peer_total,
            ratio_log,
        ) = self.compute_quantitative(
            quant_inputs,
            ratio_weights=ratio_weights,
            enable_peer_positioning=enable_peer_positioning,
            fin=fin,
        )

        qual_score, n_qual, qual_log = self.compute_qualitative(
            qual_inputs,
            qual_weights=qual_weights,
            qual_buckets=qual_buckets,
        )

        # 3. Weights between quant and qual (now using config.RATING_WEIGHTS)
        wq, wl = compute_effective_weights(
            n_quant,
            n_qual,
            self.config["RATING_WEIGHTS"],
        )
        logger.info(
            "%s-Weights: n_quant=%d n_qual=%d -> wq=%.3f wl=%.3f",
            self.cp_name,
            n_quant,
            n_qual,
            wq,
            wl,
        )

        combined_score = wq * quant_score + wl * qual_score

        # 4. Base rating and band-based outlook
        base_rating = safe_score_to_rating(
            combined_score,
            self.config["SCORE_TO_RATING"],
        )
        base_outlook, band_position = derive_outlook_band_only(
            combined_score,
            base_rating,
            self.config["SCORE_TO_RATING"],
        )
        
        # 5. Distress / hardstops
        if enable_hardstops:
            distress_notches, hardstop_details, distress_per_metric = (
                self.compute_distress_notches(fin)
            )
        else:
            distress_notches = 0
            hardstop_details = {}
            distress_per_metric = {}

        # Enrich ratio_log with distress per metric (same behavior as before)
        for row in ratio_log:
            name = row.get("Name")
            if name in {"interest_coverage", "dscr", "altman_z"}:
                row["DistressNotches"] = distress_per_metric.get(name, 0)
            else:
                row["DistressNotches"] = row.get("DistressNotches", 0)

        hardstop_rating = move_notches(
            base_rating,
            distress_notches,
            self.config["RATING_SCALE"],
        )
        hardstop_triggered = (hardstop_rating != base_rating)

        # 6. Sovereign cap
        capped_rating = hardstop_rating
        if enable_sovereign_cap and sovereign_rating is not None:
            capped_rating = apply_sovereign_cap(
                hardstop_rating,
                sovereign_rating,
                self.config["RATING_SCALE"],
            )

        final_rating = capped_rating

        sovereign_cap_binding = (
            enable_sovereign_cap
            and sovereign_rating is not None
            and final_rating == sovereign_rating
        )

        # 7. Outlook adjustments (distress trend + sovereign)
        # If no hardstops are triggered, hardstop_outlook ≈ base_outlook; outlook follows a waterfall: base → hardstop → sovereign.
        hardstop_outlook = derive_outlook_with_distress_trend(
            base_outlook,
            distress_notches,
            quant_inputs.fin_t0,
            quant_inputs.fin_t1,
        )

        if (
            sovereign_cap_binding
            and sovereign_outlook in {"Positive", "Stable", "Negative"}
        ):
            sr = sovereign_rating
            so = sovereign_outlook
            severity = {"Positive": 0, "Stable": 1, "Negative": 2}

            if is_stronger(hardstop_rating, sr,  self.config["RATING_SCALE"]):
                outlook = so                                  # Sovereign stronger → use its outlook
            else:
                if sr == hardstop_rating:
                    candidates = [hardstop_outlook, so]
                    outlook = max(candidates, key=lambda o: severity[o])
        else:
            outlook = hardstop_outlook

        if final_rating == "AAA" and outlook == "Positive" and not sovereign_cap_binding:
            outlook = "Stable"                               # No AAA with Positive in this model

        final_outlook = outlook

        
        # 8. Flags for UI / debug
        flags = {
            "enable_hardstops": enable_hardstops,
            "enable_sovereign_cap": enable_sovereign_cap and (sovereign_rating is not None),
            "enable_peer_positioning": enable_peer_positioning,
            "hardstop_triggered": hardstop_triggered,
            "sovereign_cap_binding": sovereign_cap_binding,
        }

        # 9. Human-readable explanation string
        parts: List[str] = []
        parts.append(
            f"Based on the quantitative and qualitative factors, the combined score is "
            f"{combined_score:.1f}, corresponding to a base rating of {base_rating}."
        )
        if hardstop_triggered:
            parts.append(
                f" Distress factors {list(hardstop_details.keys())} triggered a total "
                f"of {abs(distress_notches)} notch(es) of downgrade, resulting in a "
                f"post-distress (hardstop) rating of {hardstop_rating}."
            )
        else:
            parts.append(
                f" No distress-related hardstops were applied, so the hardstop rating "
                f"remains equal to the base rating at {hardstop_rating}."
            )

        if enable_sovereign_cap and sovereign_rating is not None:
            if sovereign_cap_binding:
                if hardstop_rating != capped_rating:
                    parts.append(
                        f" The sovereign cap is binding: given the sovereign rating of "
                        f"{sovereign_rating}, the rating is constrained from {hardstop_rating} "
                        f"to a capped rating of {capped_rating}."
                    )
                else:
                    parts.append(
                        f" The issuer's rating is aligned with the sovereign rating at "
                        f"{sovereign_rating}, so the sovereign cap is effectively binding."
                    )
            else:
                parts.append(
                    f" A sovereign rating of {sovereign_rating} is considered, but it does not "
                    f"constrain the issuer rating, so the capped rating remains {capped_rating}."
                )
        else:
            parts.append(
                f" No sovereign cap is applied, so the capped rating is the same as the "
                f"post-distress rating at {capped_rating}."
            )

        parts.append(
            f" The final issuer rating is {final_rating} with an outlook of {final_outlook}."
        )
        rating_explanation = "".join(parts)

        logger.info(
            "%s-Final: base=%s hardstop=%s capped=%s final=%s outlook=%s distress_notches=%d",
            self.cp_name,
            base_rating,
            hardstop_rating,
            capped_rating,
            final_rating,
            final_outlook,
            distress_notches,
        )

        # 10. Return fully populated RatingOutputs dataclass
        return RatingOutputs(
            issuer_name=self.cp_name,
            quantitative_score=quant_score,
            qualitative_score=qual_score,
            combined_score=combined_score,
            peer_score=peer_score,
            base_rating=base_rating,
            distress_notches=distress_notches,
            hardstop_rating=hardstop_rating,
            capped_rating=capped_rating,
            final_rating=final_rating,
            hardstop_triggered=hardstop_triggered,
            hardstop_details=hardstop_details,
            sovereign_rating=sovereign_rating,
            sovereign_outlook=sovereign_outlook,
            sovereign_cap_binding=sovereign_cap_binding,
            outlook=final_outlook,
            bucket_avgs=bucket_avgs,
            altman_z_t0=fin.get("altman_z"),
            flags=flags,
            rating_explanation=rating_explanation,
            peer_underperform_count=peer_under,
            peer_outperform_count=peer_over,
            peer_on_par_count=peer_on_par,
            peer_total_compared=peer_total,
            band_position=band_position,
            ratio_log=ratio_log,
            base_outlook=base_outlook,
            hardstop_outlook=hardstop_outlook,
            final_outlook=final_outlook,
            n_quant=n_quant,
            n_qual=n_qual,
            wq=wq,
            wl=wl,
            qual_log=qual_log,
        )