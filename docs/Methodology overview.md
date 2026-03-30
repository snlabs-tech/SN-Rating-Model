# SN Corporate Rating Model – Methodology

This document describes the methodology implemented in the SN Corporate Rating Model; earlier versions are deprecated. It is a transparent, rules-based framework that combines quantitative financial metrics and qualitative assessments into an issuer rating and outlook. 

---

## 1. Overview

The model produces a long-term **issuer credit rating** and **outlook** for corporates based on:

- **Quantitative** financial ratios, including coverage/leverage/profitability metrics and the Altman Z-score. 
- **Qualitative** factors covering business profile, governance, and financial policy.
- **Peer positioning**(optional), comparing the issuer’s key ratios against a peer group. 
- **Distress / hardstops**(optional), which can notch down the rating when distress indicators breach configured thresholds. 
- **Sovereign cap**(optional), which can cap the issuer rating at the sovereign rating when enabled.

The model is implemented in Python with Excel as the primary user interface for input and reporting. All configuration (bands, weights, scales) and inputs are provided via Excel, while the rating logic is executed by the Python engine.

### Running the model and generating the Excel report

The model and Excel report can be run in several ways:

- **Python script** – Call `run_from_excel_with_bands()` and then `generate_corporate_rating_report(...)`; the report is written to the `output` folder.
- **Windows batch file** – Run the provided `.bat` file, which executes the model end-to-end and produces the Excel report in the `output` folder.

---
## 2. Inputs and Data Structure

### 2.1 Excel input files

The model uses two main Excel workbooks stored in the `input` folder:

1. `sn_rating_config.xlsx`
   - The file contains the following sheets with default configuration used by the model, which can be customised.
   - This excel file will override the built-in-default configuration within the rating model.
   - Band tables for financial ratios (sheets: `lower_better`, `higher_better`).  
   - Configuration for ratio families/buckets and direction (higher is better / lower is better).
   - and optional overall `quantitative_weight` and `qualitative_weight` (e.g. 0.7 / 0.3) that override the automatic weight derivation.

3. `sn_rating_input.xlsx`  
   - `fin_ratios`: financial ratios for up to three periods (`t0`, `t1`, `t2`) plus per-ratio weights.  
   - `components`: balance sheet and P&L components used to compute Altman Z.  
   - `qual_factors`: qualitative factor values (e.g. 1–5 scale), weights, and buckets.  
   - `peers_t0`: peer group ratios per metric at `t0`.  
   - `metadata`: issuer name, sovereign rating/outlook, feature flags (peer positioning, hardstops, sovereign cap)

### 2.2 Datamodel

The Python engine organizes inputs and outputs into dataclasses:

- `QuantInputs`  
  - `fin_t0`, `fin_t1`, `fin_t2`: dictionaries of ratio name → value per period.  
  - `components_t0`, `components_t1`, `components_t2`: components for Altman Z.  
  - `peers_t0`: peer metrics as `metric → [values]`.

- `QualInputs`  
  - `factors_t0`, `factors_t1`: qualitative factor values per period.

- `RatioConfig` and `QualFactorConfig`  
  - Name (metric/factor name as used in Excel and logs), bucket (family), and weight for each ratio/factor.

- `RatingOutputs`  
  - Quantitative, qualitative, and combined scores.  
  - Base, post-distress, capped, and final ratings.  
  - Base, hardstop, and final outlooks; band position.  
  - Distress details, sovereign cap flags, peer metrics, and detailed per-ratio and per-factor logs.

Helper converters (`load_metadata_excel`, `df_row_to_dict`, `df_qual_to_dict`, `components_col_to_dict`, `peers_df_to_dict`) transform Excel sheets into the above structures.

---

## 3. Configuration and Scaling

### 3.1 Score-to-rating scale

A central configuration `SCORE_TO_RATING` maps integer score cutoffs to rating grades (e.g. 95+ → AAA, 80–89 → AA, …).

- Scores are on a 0–100 scale.  
- `score_to_rating` returns the first rating whose cutoff is less than or equal to the score.  
- `safe_score_to_rating` wraps this mapping and returns `"N/R"` when no cutoff applies.

### 3.2 Quantitative vs qualitative weights

The model uses `RATING_WEIGHTS` to combine quantitative and qualitative scores:

- If explicit weights are provided (e.g. 60% quant, 40% qual), they are applied directly.  
- Otherwise, `compute_effective_weights` derives weights proportionally to the number of active quantitative and qualitative items, ensuring both sides are represented when present.

### 3.3 Qualitative scale mapping

Qualitative factors are specified on a simple numeric scale (e.g. 1–5).

- `QUAL_SCORE_SCALE` maps each selection (1–5) to a 0–100 score.  
- `score_qual_factor_numeric` performs this mapping and returns `None` for invalid/missing entries.

---

## 4. Ratio Bands and Direction Handling

### 4.1 BandConfig and ratio families

`BandConfig` loads financial ratio bands from `sn_rating_config.xlsx`:

- Reads `lower_better` and `higher_better` sheets into DataFrames.  
- Normalizes column names and text (lowercasing, stripping).  
- For each ratio, stores:  
  - `ratio_family` (bucket/family for aggregation).  
  - `direction` (`"higher"` or `"lower"`) indicating whether higher values are better or worse.

### 4.2 Band-based scoring

For each metric, `BandConfig.lookup` maps a numeric value to a score:

- It locates the configured band where `min_value ≤ value < max_value` and returns the corresponding band `score`.  
- If the value is below the minimum or above the maximum, the score is clamped to the lowest or highest band respectively.  
- If the metric is not configured, scoring returns `None` and the ratio is skipped.

This provides a configurable, band-based mapping from ratios to standardized 0–100 scores, allowing you to shape how different ratio ranges translate into scores.

---

## 5. Quantitative Block

### 5.1 Altman Z-score

The model ensures that an Altman Z-score is available for each issuer:

- If `fin_t0["altman_z"]` is provided and finite, it is used as-is.  
- Otherwise, `_ensure_altman_z` calls `compute_altman_z_from_components` using:
  - Working capital / total assets.  
  - Retained earnings / total assets.  
  - EBIT / total assets.  
  - Market value of equity / total liabilities.  
  - Sales / total assets.  
- The computed Z-score is written back into `fin_t0` for consistency.

### 5.2 Per-ratio scoring and aggregation

`compute_quantitative` performs the quantitative scoring:

1. **Filtering and scoring**  
   - Iterates over all ratios in `fin_t0`.  
   - Skips ratios not present in `BandConfig` (no direction/bands).  
   - Uses `BandConfig.lookup` to map each ratio value to a 0–100 score.

2. **Weights and buckets**  
   - Uses `ratio_weights[metric]` if provided, otherwise defaults to `1.0`.  
   - Looks up the associated `ratio_family` from `BandConfig` (or `"OTHERS"`).  
   - Aggregates:
     - Total weighted score and total weight.  
     - Per-bucket weighted scores and weights.

3. **Peer positioning per ratio (optional)**  
   - If peer positioning is enabled and peer data exists, it computes a peer average for each ratio. 
   - `classify_peer_with_bandconfig` then:
     - Retrieves the ratio’s direction (`higher`/`lower`).  
     - Constructs an on-par band as ±10% around the peer average.  
     - Classifies the issuer as `under`, `over`, or `on_par`, direction-aware (e.g. lower leverage may be positive).  
     - Returns the lower/upper bounds, peer average, and classification flag.

4. **Ratio log**  
   - For each ratio, a log row is created capturing:
     - Name, value, score, weight, bucket.  
     - Peer average, peer on-par bounds, and peer flag (if applicable).  
     - Distress notches (filled later in the workflow).

5. **Peer score (aggregate)**  
   - After per-ratio classification, `compute_peer_score` compares each metric’s value to peer averages with ±10% thresholds and counts under/over occurrences.  
   - It returns an overall peer score (0–100) plus counts of under/over and total metrics.  
   - The peer score is treated as a separate “peer” bucket item and appended to the ratio log.

6. **Quantitative score**

   - The final quantitative score is the weighted average of all ratio and peer scores:

       - QuantitativeScore = (Σ wᵢ · scoreᵢ) / (Σ wᵢ)

   - Per-bucket averages are also computed for reporting.


---

## 6. Qualitative Block

`compute_qualitative` transforms qualitative factor selections into a weighted score:

1. **Filtering**  
   - Iterates over `factors_t0`.  
   - Skips `None` or NaN values.

2. **Scoring and weights**  
   - Uses `score_qual_factor_numeric` to map each factor value (e.g. 1–5) to a 0–100 score.  
   - Applies factor-specific weights from `qual_weights` (default 1.0).  
   - Assigns factors to buckets via `qual_buckets` (or `"OTHERS"`).

3. **Aggregation**  
   - Computes the weighted average of qualitative scores:

     QualitativeScore = (Σ wⱼ · sⱼ) / (Σ wⱼ)

   - Builds a `qual_log` listing factors, values, scores, weights, and buckets.

---

## 7. Combining Quantitative and Qualitative Blocks

### 7.1 Effective weights

Given `n_quant` and `n_qual` active items:

`compute_effective_weights` either:
- Uses configured weights, or
- Derives weights as:

  w_q = n_quant / (n_quant + n_qual)  
  w_l = 1 − w_q


### 7.2 Combined score and base rating

The combined score is computed as:

CombinedScore = w_q · QuantitativeScore + w_l · QualitativeScore


- `safe_score_to_rating` maps this combined score to a `base_rating`.  
- `get_rating_band` returns the numeric score band for `base_rating`.  
- `derive_outlook_band_only` then assigns:
  - Outlook (`Positive`, `Stable`, `Negative`) based on where the combined score sits within the band.  
  - Band position (`upper_band`, `middle_band`, `lower_band`).

---

## 8. Distress / Hardstops

The model incorporates explicit distress triggers to prevent overly high ratings when financial distress indicators are weak.

### 8.1 Distress bands

`DISTRESS_BANDS` defines thresholds and notches for:

- `interest_coverage`.  
- `dscr`.  
- `altman_z`.

Each band is defined as `(threshold, notches)` where notches are typically negative (downgrade).

### 8.2 Computing distress notches

`compute_distress_notches`:

- Checks `interest_coverage` and `dscr` in `fin_t0` against their distress bands.  
- Checks `altman_z` against its distress bands.  
- For each metric, the first breached threshold determines its notches.  
- Sums all notches into `total_notches`.  
- Applies a cap using `MAX_DISTRESS_NOTCHES` to avoid excessive downgrades.

It returns:

- `total_notches`.  
- A `details` dictionary capturing which metrics triggered distress and their values.  
- `per_metric_notches` capturing notches per distress metric.

### 8.3 Applying distress to ratings and outlook

If hardstops are enabled:

- The base rating (from combined score) is adjusted via `move_notches` using `distress_notches`.  
- `hardstop_rating` may be weaker than the base rating.  
- Each distress metric in the ratio log is annotated with its `DistressNotches`.  
- `derive_outlook_with_distress_trend` can override the band-based outlook:
  - If distress notches are negative and distress ratios are deteriorating between `t1` and `t0`, outlook may be forced to `Negative`.  
  - If trends are improving, outlook may remain `Stable`.

---

## 9. Sovereign Cap Logic

When enabled, the sovereign cap constrains the issuer rating relative to the sovereign rating.

- `apply_sovereign_cap`:
  - Compares the notched (hardstop) rating and the sovereign rating within `RATING_SCALE`.  
  - Sets the issuer rating to the weaker of the two.  
- A flag `sovereign_cap_binding` is set if the cap actively constrains the issuer rating.

Outlook handling with sovereign cap:

- If the cap is binding and a valid sovereign outlook is provided:
  - If the issuer’s hardstop rating is stronger than the sovereign, the model adopts the sovereign outlook.  
  - If ratings are the same, the model chooses the more conservative outlook between the sovereign and model-implied outlook.  
- The model prohibits `AAA` with `Positive` outlook unless constrained by sovereign, normalizing to `AAA/Stable` in that case.

---

## 10. RatingModel Orchestration

The `RatingModel` class encapsulates the full workflow:

1. **Quantitative block** – `compute_quantitative`  
   - Ensures Altman Z is available.  
   - Scores ratios via `BandConfig`.  
   - Applies weights and aggregates by bucket.  
   - Performs peer positioning per ratio and computes an aggregate peer score.  

2. **Qualitative block** – `compute_qualitative`  
   - Scores qualitative factors using `QUAL_SCORE_SCALE`.  
   - Applies weights and buckets, logs details.

3. **Combine and map to rating**  
   - Computes effective weights `wq`, `wl`.  
   - Combines quantitative and qualitative scores.  
   - Maps to base rating and band-based outlook.

4. **Distress / hardstops**  
   - Optionally computes distress notches and applies them to get `hardstop_rating`.  
   - Annotates ratio logs with distress notches.  
   - Derives `hardstop_outlook` based on distress trends.

5. **Sovereign cap**  
   - Optionally applies sovereign cap to produce `capped_rating`.  
   - Determines whether the cap is binding.

6. **Final rating and outlook**  
   - Produces `final_rating` and `final_outlook` after all constraints.  
   - Sets flags for hardstop, sovereign cap, peer positioning.

7. **Explanation and logs**  
   - Builds a human-readable `rating_explanation` summarizing key drivers:
     - Combined score and base rating.  
     - Distress impact (if any).  
     - Sovereign cap effect (if any).  
     - Final rating and outlook.  
   - Returns a fully populated `RatingOutputs` with:
     - Scores, ratings, outlooks, band position.  
     - Distress and sovereign details.  
     - Peer stats.  
     - `ratio_log` and `qual_log`.

---

## 11. Excel reporting and execution context

### 11.1 Excel rating report

`generate_corporate_rating_report(result)` creates a multi-sheet Excel report and saves it in the `output` folder, using the issuer name in the filename (for example: `ACME_INC_Corporate_Credit_Rating_Report.xlsx`).

- **Rating Report** (main sheet):
  - Issuer identification, internal reference, report date, and model version.
  - Selected quantitative ratios and qualitative factors for `t0` and `t1`.
  - Quantitative, qualitative, combined scores and key rating snapshots:
    - Base, hardstop, final rating and outlook.
  - Flags block (hardstops, sovereign cap, peer positioning, distress notches).
  - Narrative rating rationale.

- **log** sheet:
  - Detailed ratio log including value, score, weight, peer averages, peer bounds and flags, distress notches.
  - Aggregate peer counts and scores.
  - Overall score, band range, and rating/outlook snapshots.

- **qual_log** sheet:
  - Per-factor qualitative log with values, scores, weights, and buckets.

### Execution context

The same methodology is applied whether the model is run from a Python notebook/script, a Windows batch file, or a packaged executable; in all cases, inputs are read from the `input` folder and the Excel rating report is written to the `output` folder.

### 11.2 Excel-driven runner

`run_from_excel_with_bands(horizon="t0")` is the high-level entry point:

- Loads configuration and input workbooks from the `input` folder.  
- Infers time labels and constructs `QuantInputs` and `QualInputs`.  
- Reads feature flags and sovereign information from metadata.  
- Instantiates `RatingModel` and calls `compute_final_rating`.  
- Returns `RatingOutputs`, which can then be passed to `generate_corporate_rating_report`.

---

## 12. Intended Use and Limitations

This model is a **rules-based scoring framework**, not a calibrated rating-agency model.

- It is designed for internal analysis, scenario testing, and educational purposes.  
- Bands, weights, and qualitative scales are configurable and should be tailored to the user’s portfolio, industry, and risk appetite.  
- Outputs should be interpreted as **relative** indications of credit strength and not as a substitute for full credit committee analysis.

Users are encouraged to adjust band tables, weights, and qualitative definitions to align the model with their internal methodology and to validate its behavior on historical cases before relying on it in production.
