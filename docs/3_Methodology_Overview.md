# SN Corporate Rating Model – Methodology

This document describes the methodology implemented in the SN Corporate Rating Model; earlier versions are deprecated. It is a transparent, rules-based framework that combines quantitative financial metrics and qualitative assessments into an issuer rating and outlook.

---

## 1. Overview

The model produces a long-term **issuer credit rating** and **outlook** for corporates based on:

- **Quantitative** financial ratios, including coverage, leverage, profitability metrics, and the Altman Z-score.
- **Qualitative** factors covering business profile, governance, and financial policy.
- **Peer positioning** (optional), comparing the issuer’s key ratios against a peer group.
- **Distress / hardstops** (optional), which can notch down the rating when distress indicators breach configured thresholds.
- **Sovereign cap** (optional), which can cap the issuer rating at the sovereign rating when enabled.

The model is implemented in Python with Excel as the primary user interface for input and reporting. Configuration (bands, weights, scales) and inputs are provided via Excel, while the rating logic is executed by the Python engine.

---

## 2. Intended use

This model is intended for educational, exploratory, and internal analytical use. It is **not** a PD‑calibrated, rating‑agency‑validated model and should not be treated as such.

The default ratios, bands, and rating scale shipped with the tool are illustrative; they demonstrate how the framework works rather than representing any particular agency methodology. Users must define their own ratios, bands, and score‑to‑rating scale to reflect their internal views and should validate the configuration against their own historical data and policies before relying on outputs.

---

## 3. Inputs and data structure

### 3.1 Excel input workbook (`sn_rating_input.xlsx`)

The model uses `input/sn_rating_input.xlsx` as the primary input workbook.

Sheets:

- `metadata`  
  - Key/value pairs, including:
    - `name`, `country`, `id`
    - `sovereign_rating`, `sovereign_outlook`
    - `enable_peer_positioning`, `enable_hardstops`, `enable_sovereign_cap`
  - Feature flags control whether peer positioning, distress hardstops, and sovereign cap are applied.

- `fin_ratios`  
  - Columns:
    - `metric`: ratio code (e.g. `debt_ebitda`, `interest_coverage`, `dscr`, `roa`).
    - `weight`: optional per-ratio weight (blank → 1.0).
    - Period columns: remaining non-helper columns (e.g. `FY25`, `FY24`, `FY23` or similar).
  - The model infers time labels using `_infer_time_labels`:
    - T0 = first non-helper column (most recent period).
    - T1 = second column.
    - T2 = third column (or T1 reused if only two periods are provided).
  - These values are loaded into `QuantInputs.fin_t0/fin_t1/fin_t2` and `ratio_weights`.

- `components`  
  - Indexed by component code (e.g. `working_capital`, `total_assets`, `retained_earnings`, `ebit`, `market_value_equity`, `total_liabilities`, `sales`).
  - Columns use the same T0/T1/T2 labels as inferred from `fin_ratios`.
  - Used to compute Altman Z-score when not provided as a ratio explicitly.

- `qual_factors`  
  - Columns:
    - `factor`: qualitative factor code.
    - `weight`: optional per-factor weight (blank → 1.0).
    - `bucket`: optional grouping label (blank → `"OTHERS"`).
    - Period columns: non-helper columns; T0 = first, T1 = second.
  - Loaded into `QualInputs.factors_t0/factors_t1`, with `qual_weights` and `qual_buckets` constructed from `weight` and `bucket`.

- `peers_t0`  
  - First column: ratio code (renamed to `metric` and used as index).
  - Remaining columns: peer values for that ratio.
  - Converted into `peers_t0 = {metric: [values...]}`, used for per-metric and aggregate peer positioning.

Unnamed Excel columns (e.g. artifacts from formatting) are ignored in `fin_ratios`, `components`, `qual_factors`, and `peers_t0` so layout noise does not break the loaders.

---

## 4. Configuration methodology (`sn_rating_config.xlsx`)

The configuration workbook `input/sn_rating_config.xlsx` is the primary way to customize the model without changing Python code. At runtime, the model:

- Loads defaults from `config.py`.
- Reads `sn_rating_config.xlsx` (if present).
- Applies Excel overrides on top of the defaults.
- Falls back to code defaults wherever the file, sheet, row, or cell is missing.

Each sheet is optional. Missing sheets or entries never break the run; they only cause the model to use built-in defaults instead.

### 4.1 Supported configuration sheets

The following sheets are recognized:

1. `score_to_rating`
2. `qual_score_scale`
3. `lower_better`
4. `higher_better`
5. `distress_bands`
6. `others`

If a sheet is not present, the corresponding section of the default config in `config.py` is used.

### 4.2 score_to_rating

Defines how the combined 0–100 score maps to rating grades (AAA, AA+, …, C).

**Expected columns**

- `threshold` (numeric)
- `rating` (string)

Each non-blank row becomes a `(threshold, rating)` pair. The model:

- Sorts these pairs from highest to lowest threshold.
- Uses them in `safe_score_to_rating` to map combined scores to ratings.
- Derives the ordered `RATING_SCALE` from this table, used for:
  - Notch adjustments (`move_notches`).
  - Sovereign cap (`apply_sovereign_cap`).
  - Rating comparisons (`is_stronger`, `is_weaker_or_equal`).

If `score_to_rating` is missing or empty, the built-in `DEFAULT_SCORE_TO_RATING` table in `config.py` is used.

### 4.3 qual_score_scale

Controls how 1–5 qualitative scores are mapped to a numeric (0–100) scale.

**Expected columns**

- `score` (integer, usually 1–5)
- `boost_pct` (numeric, 0–100)

The model builds a dictionary `{score: boost_pct}` and uses it in:

- `score_qual_factor_numeric`
- `compute_qualitative`

Factors whose value is blank/NaN or not present in this mapping are skipped.

If `qual_score_scale` is missing, the default mapping from `config.py` is used.

### 4.4 lower_better and 4.5 higher_better

These two sheets define the banded scoring rules for each ratio and whether lower or higher values are better.

**Expected columns**

- `ratio_family` (e.g. `leverage`, `coverage`, `profit`, `altman`, `other`)
- `ratio_name` (e.g. `debt_ebitda`, `interest_coverage`, `roa`)
- `min_value` (numeric, inclusive lower bound)
- `max_value` (numeric, exclusive upper bound)
- `score` (numeric, typically 0, 25, 50, 75, 100)

The model:

- Reads all non-blank rows from `lower_better` and `higher_better`.
- Groups bands by `(ratio_family, ratio_name)`.
- Builds `RATIOS_LOWER_BETTER` and `RATIOS_HIGHER_BETTER` dictionaries.
- Passes them into `BandConfig`, which:
  - Normalizes names/families (lowercase, stripped).
  - Records each ratio’s direction (`lower` or `higher` is better).
  - Provides `lookup(metric, value)` → band score (0–100).

**How the model uses bands**

- Quantitative scoring:
  - Only ratios that have bands defined in `BandConfig` are scored.
  - For each metric, the model finds the band where `min_value <= value < max_value` and assigns its 0–100 score.
  - If a value falls below the minimum or above the maximum configured thresholds, it is clamped to the lowest or highest band score for that ratio.
- Peer positioning:
  - The ratio’s direction (higher vs lower is better) comes from `BandConfig`.
  - Metrics without a known direction are skipped in peer scoring.

**Adding or changing ratios**

- To change scoring for existing ratios, edit or replace the bands for that `(ratio_family, ratio_name)` in the appropriate sheet.
- To introduce a new ratio (new row in `fin_ratios`), you must also:
  - Add bands for it in `higher_better` or `lower_better`.
  - Then the model will:
    - Include it in the quantitative score.
    - Use it in peer positioning (if peer data exists).

If either sheet is missing, the defaults from `DEFAULT_RATIOS_LOWER_BETTER` / `DEFAULT_RATIOS_HIGHER_BETTER` in `config.py` are used.

### 4.6 distress_bands

This sheet drives the distress / hardstop logic, determining when key metrics trigger notch downgrades.

**Expected columns**

- `metric` (e.g. `interest_coverage`, `dscr`, `altman_z`)
- `threshold` (numeric)
- `notches_down` (integer, typically negative)

The model:

- Groups rows by metric.
- For each metric, sorts thresholds ascending and applies the first rule where `value <= threshold`.
- Sums `notches_down` across all metrics to get `distress_notches`.
- Applies a floor using `MAX_DISTRESS_NOTCHES` from the `others` sheet.

If `distress_bands` is missing, the default `DEFAULT_DISTRESS_BANDS` from `config.py` is used.

### 4.7 others

Provides scalar configuration values.

**Expected columns**

- `metric`
- `threshold` (numeric)

Recognised metrics:

- `MAX_DISTRESS_NOTCHES`
  - Caps the total downward distress adjustment to this value.

- `quantitative_weight`
- `qualitative_weight`
  - If **both** are provided and positive:
    - The model normalizes them so `wq + wl = 1.0`.
    - Uses them as global weights between quantitative and qualitative blocks when computing the combined score.
  - If one or both are missing:
    - The model falls back to count-based weights using `n_quant` and `n_qual` (number of metrics actually used).

If `others` is missing, the defaults from `config.py` are used:

- `MAX_DISTRESS_NOTCHES = -4`
- `RATING_WEIGHTS = {"quantitative": None, "qualitative": None}` (which triggers count-based weights).

### 4.8 Interaction with built-in defaults

`config.py` still contains complete default definitions for:

- `DEFAULT_SCORE_TO_RATING` and derived `DEFAULT_RATING_SCALE`
- `DEFAULT_RATIOS_LOWER_BETTER` / `DEFAULT_RATIOS_HIGHER_BETTER`
- `DEFAULT_DISTRESS_BANDS` and `DEFAULT_MAX_DISTRESS_NOTCHES`
- `DEFAULT_QUAL_SCORE_SCALE`
- `DEFAULT_RATING_WEIGHTS`

At load time:

1. A configuration dictionary is initialised from these defaults.
2. Each Excel sheet (if present) updates only its relevant keys.
3. Any metric, band, or parameter not specified in Excel retains the code default.

This design allows you to:

- Fully customise the configuration purely in Excel.
- Partially customise (override only what you care about) without copying all defaults.
- Add new ratios to the input workbook and make them active in the model by defining their bands in `higher_better` or `lower_better`, while still relying on built-in bands for everything else.

---

## 5. Datamodel

The Python engine organizes inputs and outputs into dataclasses.

- `QuantInputs`  
  - `fin_t0`, `fin_t1`, `fin_t2`: dicts of ratio name → value per period.
  - `components_t0`, `components_t1`, `components_t2`: component values per period for Altman Z.
  - `peers_t0`: dict `metric → [values]` for peer ratios.
  - `ratio_weights`: dict `metric → weight`, defaulting to 1.0 when not specified.

- `QualInputs`  
  - `factors_t0`, `factors_t1`: qualitative factor values per period (e.g. 1–5).

- `RatingOutputs`  
  - Scores: `quantitative_score`, `qualitative_score`, `combined_score`, `peer_score`.
  - Ratings: `base_rating`, `hardstop_rating`, `capped_rating`, `final_rating`.
  - Outlooks: `base_outlook`, `hardstop_outlook`, `final_outlook`, `band_position`.
  - Distress/sovereign: `distress_notches`, `hardstop_details`, `sovereign_rating`, `sovereign_outlook`, `sovereign_cap_binding`.
  - Peer stats: `peer_underperform_count`, `peer_outperform_count`, `peer_on_par_count`, `peer_total_compared`.
  - Diagnostics: `bucket_avgs`, `altman_z_t0`, `flags`, `rating_explanation`, `ratio_log`, `qual_log`, `n_quant`, `n_qual`, `wq`, `wl`.

Helper converters (`load_metadata_excel`, `components_col_to_dict`, `peers_df_to_dict`, etc.) transform Excel sheets into these structures.

---

## 6. Score-to-rating scale and weights

### 6.1 Score-to-rating mapping

A central configuration `SCORE_TO_RATING` maps integer score cutoffs to rating grades (e.g. 95+ → AAA, 80–89 → AA, …).

- Combined scores are on a 0–100 scale.
- `score_to_rating` returns the first rating whose cutoff is less than or equal to the score.
- `safe_score_to_rating` wraps this mapping and returns `"NR"` if no cutoff applies.

### 6.2 Quantitative vs qualitative weights

The model uses `RATING_WEIGHTS` and `compute_effective_weights` to combine quantitative and qualitative scores.

- If explicit `quantitative_weight` and `qualitative_weight` are provided in the `others` sheet, they are normalised so that `wq + wl = 1.0` and used directly.
- Otherwise, weights are derived from counts:
  - `wq = n_quant / (n_quant + n_qual)`
  - `wl = n_qual / (n_quant + n_qual)`

This ensures that when no explicit weights are set, both blocks contribute in proportion to the number of valid metrics/factors used.

---

## 7. Ratio bands and direction handling

### 7.1 BandConfig and ratio families

`BandConfig` loads financial ratio bands from the merged configuration.

- It converts `RATIOS_LOWER_BETTER` and `RATIOS_HIGHER_BETTER` into internal DataFrames.
- It normalizes text columns and builds lookup tables:
  - `ratio_family[ratio_name]` → family/bucket.
  - `direction[ratio_name]` → `"higher"` or `"lower"`.

This allows downstream logic to treat each metric consistently when scoring and in peer comparisons.

### 7.2 Band-based scoring

For each metric, `BandConfig.lookup(metric, value)` maps a numeric value to a score.

- It finds the configured band where `min_value ≤ value < max_value` and returns the band score.
- If no band matches but bands exist for that metric, the value is clamped to the lowest/highest band score.
- If the metric has no bands configured at all, the function returns `None` and the metric is excluded from quantitative scoring.

---

## 8. Quantitative block

### 8.1 Altman Z-score

The model ensures an Altman Z-score is available for each issuer.

- If `fin_t0["altman_z"]` is present and finite, it is used directly.
- Otherwise, `_ensure_altman_z` computes it from `components_t0` using:
  - Working capital / total assets.
  - Retained earnings / total assets.
  - EBIT / total assets.
  - Market value of equity / total liabilities.
  - Sales / total assets.

The computed Z-score is stored back into `fin_t0` and logged.

### 8.2 Per-ratio scoring and aggregation

`compute_quantitative` performs quantitative scoring.

1. **Filtering and scoring**  
   - Iterates over ratios in `fin_t0` and skips those without configured bands or direction.
   - Uses `BandConfig.lookup` to map each value to a 0–100 score.

2. **Weights and buckets**  
   - Uses `ratio_weights[metric]` if available, otherwise 1.0.
   - Derives the bucket from `BandConfig.ratio_family[metric]` (or `"OTHERS"` if missing).
   - Aggregates:
     - Total weighted sum and total weight.
     - Per-bucket weighted sums and weights, later turned into `bucket_avgs`.

3. **Per-ratio peer positioning (optional)**  
   - If peer positioning is enabled and `peers_t0` is non-empty:
     - Computes a peer average per ratio from the peer list.
     - Calls `classify_peer_with_bandconfig`:
       - Uses the ratio’s direction from `BandConfig`.
       - Defines an on-par band as ±10% around the peer average.
       - Classifies each ratio as `under`, `over`, or `on_par`.

4. **Ratio log**  
   - Records, for each ratio:
     - `Name`, `Value`, `Score`, `Weight`, `Bucket`.
     - `PeerFlag`, `PeerAvg`, `PeerLowerBound`, `PeerUpperBound`.
     - `DistressNotches` (filled later by the distress block).

5. **Peer score (aggregate)**  
   - `compute_peer_score` uses the same direction-aware classification to compute:
     - `peer_score` (0–100) based on the share of underperforming metrics.
     - Counts of `peer_under`, `peer_over`, `peer_on_par`, `peer_total`.
   - If `peer_score` is available, it is treated as a separate quantitative item (weight 1.0, bucket `"peer"`) and added to the aggregation.

6. **Quantitative score**  

The final quantitative score is:

QuantScore = (Σ w_i · score_i) / (Σ w_i)

Per-bucket averages are computed from per-bucket sums and weights.

---

## 9. Qualitative block

`compute_qualitative` transforms qualitative factor selections into a weighted score.

1. **Filtering**  
   - Iterates over `factors_t0` and skips `None` or NaN values.

2. **Scoring and weights**  
   - Uses `score_qual_factor_numeric` with `QUAL_SCORE_SCALE` to convert each factor value (1–5) into a 0–100 score.
   - Applies factor-specific weights from `qual_weights` (default 1.0).
   - Assigns factors to buckets via `qual_buckets` (default `"OTHERS"`).

3. **Aggregation and log**  

The final qualitative score is:

QualScore = (Σ w_j · s_j) / (Σ w_j)

`qual_log` records `Name`, `Value`, `Score`, `Weight`, `Bucket` per factor.

---

## 10. Combining blocks and base rating

### 10.1 Effective weights and combined score

Using `compute_effective_weights`, the model computes `wq` and `wl` based on configuration and counts.

- If both `quantitative_weight` and `qualitative_weight` are set, they are normalized.
- Otherwise, weights are derived from `n_quant` and `n_qual` as described above.

The combined score is:

CombinedScore = w_q · QuantScore + w_l · QualScore

### 10.2 Base rating, band, and base outlook

- `safe_score_to_rating` maps `combined_score` to `base_rating` using `SCORE_TO_RATING`.
- `get_rating_band` returns `(band_min, band_max)` for `base_rating`.
- `derive_outlook_band_only` then:
  - Floors the combined score to an integer.
  - Assigns an initial outlook:
    - `Positive` if the score is at or above the band’s upper edge.
    - `Negative` if at or below the band’s lower edge.
    - `Stable` otherwise.
  - Classifies `band_position` as `upper_band`, `middle_band`, or `lower_band`.

This results in `base_rating`, `base_outlook`, and `band_position`.

---

## 11. Distress / hardstops

The model incorporates explicit distress triggers to constrain ratings when coverage or solvency metrics are weak.

### 11.1 Distress notches

`compute_distress_notches`:

- Uses `DISTRESS_BANDS` for `interest_coverage`, `dscr`, and `altman_z`.
- For each metric, finds the first threshold where the observed value is less than or equal to the threshold and applies the corresponding `notches_down`.
- Sums these to `distress_notches`.
- Applies `MAX_DISTRESS_NOTCHES` as a floor (e.g. never less severe than −4 once distress is triggered).

It returns:

- `distress_notches` (negative or zero).
- `hardstop_details` (metric → value).
- `distress_per_metric` (metric → notches).

These notches are written into the `ratio_log` as `DistressNotches` for `interest_coverage`, `dscr`, and `altman_z`.

### 11.2 Hardstop rating and hardstop outlook

If hardstops are enabled:

- `hardstop_rating = move_notches(base_rating, distress_notches, RATING_SCALE)`.
- `hardstop_triggered` is set if `hardstop_rating != base_rating`.
- `hardstop_outlook = derive_outlook_with_distress_trend(base_outlook, distress_notches, fin_t0, fin_t1)` adjusts the outlook based on distress trends.

If hardstops are disabled, `distress_notches = 0`, `hardstop_rating = base_rating`, and `hardstop_outlook = base_outlook`.

---

## 12. Sovereign cap and final outlook

### 12.1 Sovereign cap

If sovereign cap is enabled and a sovereign rating is provided:

- `capped_rating = apply_sovereign_cap(hardstop_rating, sovereign_rating, RATING_SCALE)` ensures the issuer is not rated stronger than the sovereign.
- `final_rating` is set to `capped_rating`.
- `sovereign_cap_binding` is `True` if the cap actually constrains the issuer rating.

If sovereign cap is disabled or no sovereign rating is provided, `final_rating = hardstop_rating` and `sovereign_cap_binding = False`.

### 12.2 Final outlook waterfall

The outlook logic follows a waterfall:

1. Start from `hardstop_outlook` (already incorporating distress trends).
2. If `sovereign_cap_binding` is `True` and `sovereign_outlook` is one of `{Positive, Stable, Negative}`:
   - If the hardstop rating is stronger than the sovereign rating, adopt the sovereign outlook.
   - If the hardstop rating equals the sovereign rating, choose the more conservative outlook between `hardstop_outlook` and `sovereign_outlook`.
3. Apply model-specific constraint: if `final_rating == "AAA"` and the calculated outlook is `Positive` with no sovereign cap binding, normalize to `AAA/Stable` (no standalone AAA/Positive allowed).

The result is `final_outlook`.

Flags capture which mechanisms were active:

- `enable_hardstops`, `enable_sovereign_cap`, `enable_peer_positioning`.
- `hardstop_triggered`, `sovereign_cap_binding`.

---

## 13. RatingModel orchestration

The `RatingModel` class encapsulates the end-to-end flow.

1. **Quantitative block** – `compute_quantitative`  
   - Ensures Altman Z is present or computed.
   - Scores ratios with `BandConfig`.
   - Aggregates by weights and buckets.
   - Computes per-ratio peer flags and an aggregate peer score (optional).

2. **Qualitative block** – `compute_qualitative`  
   - Maps factor scores via `QUAL_SCORE_SCALE`.
   - Applies factor weights and buckets.
   - Produces `qualitative_score` and `qual_log`.

3. **Combine and map to base rating**  
   - Determines `wq`, `wl` from configuration and counts.
   - Computes `combined_score`.
   - Maps to `base_rating`, `base_outlook`, and `band_position`.

4. **Distress / hardstops**  
   - Computes `distress_notches`, `hardstop_details`, `distress_per_metric` if enabled.
   - Computes `hardstop_rating` and `hardstop_outlook`.
   - Annotates key ratios with `DistressNotches`.

5. **Sovereign cap**  
   - Applies sovereign cap (if enabled) to obtain `final_rating`.
   - Sets `sovereign_cap_binding` flag.

6. **Final outlook**  
   - Applies the sovereign outlook logic and AAA/Positive constraint.
   - Produces `final_outlook`.

7. **Explanation and outputs**  
   - Builds a narrative `rating_explanation` summarizing:
     - Combined score and base rating.
     - Distress/hardstop effects.
     - Sovereign cap impact (if any).
     - Final rating and outlook.
   - Returns a fully populated `RatingOutputs` with all scores, ratings, outlooks, flags, and logs.

---

## 14. Excel reporting and execution context

### 14.1 Excel rating report

`generate_corporate_rating_report(result)` creates a multi-sheet Excel report and saves it in the `output` folder.

- **Rating Report** (main sheet):
  - Issuer identification, internal reference ID, report date, and model version.
  - Selected quantitative ratios and qualitative factors for T0 and T1, read from `sn_rating_input.xlsx`.
  - Quantitative, qualitative, and combined scores.
  - Base, hardstop, and final rating/outlook.
  - Flags (peer positioning enabled, hardstops enabled, sovereign cap enabled, hardstop triggered, distress_notches, sovereign rating/outlook).
  - Narrative rating rationale (`rating_explanation`).

- **ratio_log** sheet:
  - Detailed ratio log including value, score, weight, bucket, peer averages, peer bounds, peer flags, and distress notches.
  - Summary rows for:
    - Peer under/over/on_par counts and total compared.
    - Peer score.
    - Aggregate quantitative and qualitative scores.
    - `n_quant/weights`, `n_qual/weights`, `combined_score`.
    - `band_position` and base rating band range.

- **qual_log** sheet:
  - Per-factor qualitative log with values, scores, weights, and buckets.

### 14.2 Excel-driven runner

`run_from_excel_with_bands(horizon="t0")` is the high-level entry point used by `run_sn_rating.py`.

- Loads configuration and input workbooks from the `input` folder.
- Infers time labels and constructs `QuantInputs` and `QualInputs`.
- Reads feature flags and sovereign information from `metadata`.
- Instantiates `RatingModel` with the issuer name and `BandConfig`.
- Calls `compute_final_rating` and returns `RatingOutputs`.

The same methodology applies whether the model is run from a script, notebook, or packaged executable.

---

## 15. Intended use and limitations (detailed)

This model is a rules-based scoring framework, not a calibrated rating-agency model.

- It is designed for educational, exploratory, and internal analytical purposes.
- Bands, weights, qualitative scales, and the score-to-rating mapping are fully configurable and should be tailored to the user’s portfolio, industry, and risk appetite.
- The default configuration is intended for demonstration and is not meant to represent any specific agency’s criteria or to guarantee alignment with “industry standard” ratings.

Each user is responsible for:

- Selecting financial and qualitative ratios that are appropriate for their use case.
- Defining ratio bands and directions for those ratios in the configuration Excel.
- Specifying the score-to-rating scale (`score_to_rating`) and qualitative mapping (`qual_score_scale`).
- Validating and, if necessary, calibrating the configuration against their own historical data and policies.

Outputs should be interpreted as relative indicators of credit strength and as a transparent, configurable framework, not as a substitute for full credit committee analysis or official rating-agency opinions.
