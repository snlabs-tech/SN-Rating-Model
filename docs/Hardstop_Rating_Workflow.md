# Hardstop Rating Workflow

This document explains how the model applies **distress hardstops** to notch the rating down when key risk indicators signal elevated distress. It also describes how the resulting **hardstop rating** interacts with the unconstrained (base) rating and, indirectly, with the sovereign cap and outlook.

The goal is to prevent situations where strong averages or good profitability fully offset near-default coverage or Altman Z-score metrics.

---

## 1. Distress Layer in the Rating Stack

The rating is built in three main layers:

1. **Base rating (unconstrained)**  
   Derived from the combined quantitative and qualitative score using `SCORE_TO_RATING` (no distress overlay, no sovereign cap).

2. **Distress hardstops (this layer, optional)**  
   Apply notch-down adjustments based on:
   - `interest_coverage`
   - `dscr`
   - `altman_z`

3. **Sovereign cap (optional)**  
   Ensures the final issuer rating is not better than the specified sovereign rating when the cap is enabled.

The **hardstop rating** is the outcome after applying the distress layer to the base rating. When `enable_hardstops` is `False`, the hardstop rating is equal to the base rating and the distress layer is effectively inactive.

---

## 2. Distress Metrics and Bands

Three metrics are used for hardstops:

- `interest_coverage` — interest coverage ratio  
- `dscr` — debt service coverage ratio  
- `altman_z` — Altman Z-score  

Each metric has a set of **bands** with associated **negative notches**, configured via `DISTRESS_BANDS`:

```python
DISTRESS_BANDS = {
    "interest_coverage": [
        (0.5, -4),
        (0.8, -3),
        (1.0, -2),
    ],
    "dscr": [
        (0.8, -3),
        (0.9, -2),
        (1.0, -1),
    ],
    "altman_z": [
        (1.2, -4),
        (1.5, -3),
        (1.81, -2),
    ],
}

MAX_DISTRESS_NOTCHES = -4
```

### Interpretation (example for `interest_coverage`)

* `interest_coverage < 0.5` → −4 notches
* `0.5 ≤ interest_coverage < 0.8` → −3 notches
* `0.8 ≤ interest_coverage < 1.0` → −2 notches
* `interest_coverage ≥ 1.0` → no downgrade from this metric

The same pattern applies to `dscr` and `altman_z`: the model looks for the first threshold that the metric falls below and applies the corresponding negative notches.

---
## 3. How Distress Notches Are Calculated

Core function in the engine:

```python
def compute_distress_notches(
    fin: Dict[str, float],
    altman_z: float,
) -> Tuple[int, Dict[str, float], Dict[str, int]]:
    ...
```
It returns:

- `total_notches` (integer, typically 0 or negative)

- `details` (metric → value at t0)

- `per_metric_notches` (metric → notches applied)

Step-by-step logic

Interest coverage
- Read `ic = fin.get("interest_coverage")`.

- If present, iterate through DISTRESS_BANDS["interest_coverage"] in order.

- For the first `(threshold, notches)` with `ic < threshold`:

   - Add `notches` (negative) to `total_notches`.

   - Store `ic` in details["interest_coverage"].

   - Store `notches` in `per_metric_notches["interest_coverage"]`.

   - Stop checking further thresholds for this metric.

If no threshold is breached, this metric does not contribute.

DSCR
- Same pattern using `DISTRESS_BANDS["dscr"]` and `fin.get("dscr")`.

- Add any negative notches to `total_notches`.

- Store the value in `details["dscr"]` and the notches in `per_metric_notches["dscr"]` if triggered.

Altman Z
- Compare `altman_z` (already computed or supplied) to `DISTRESS_BANDS["altman_z"]`.
- On the first breached threshold:

   - Add notches to `total_notches`.

   - Store the score in `details["altman_z"]`.

   - Store notches in `per_metric_notches["altman_z"]`.

Cap the total
After aggregating contributions from all three metrics, apply the floor:
- If `total_notches < MAX_DISTRESS_NOTCHES`, set `total_notches = MAX_DISTRESS_NOTCHES`.

This limits the overall downgrade from distress to a maximum number of notches (e.g. −4).

---

## 4. Applying the Hardstop Rating

Within `compute_final_rating` the distress overlay is optional and controlled by a flag.

## 4.1 Activation

```python
if enable_hardstops:
    distress_notches, hardstop_details, distress_per_metric = self.compute_distress_notches(
        quant_inputs.fin_t0,
        altman_z,
    )
else:
    distress_notches = 0
    hardstop_details = {}
    distress_per_metric = {}
```
When enable_hardstops is False, the layer is fully inactive and no downgrade is applied.

## 4.2 From Base Rating to Hardstop Rating

The model then applies the notches to the base rating:
```Python
hardstop_rating = move_notches(base_rating, distress_notches)
hardstop_triggered = (hardstop_rating != base_rating)
```
`move_notches` shifts the rating down the internal `RATING_SCALE` by the number of notches (negative values mean moving to weaker grades, with clamping at the ends of the scale).

- If `distress_notches == 0`, `hardstop_rating` equals `base_rating` and `hardstop_triggered` is `False`.

- If `distress_notches < 0`, the hardstop rating is weaker than the base rating and `hardstop_triggered` is True.

## 4.3 Enriching the Ratio Log

For transparency, distress information is added back into the quantitative ratio log:

- For **interest_coverage, dscr**, and **altman_z**, the corresponding `DistressNotches` from `per_metric_notches` are written into each row.

- For all other ratios, `DistressNotches` is set to `0` (or left unchanged if already present).

This allows users to see, per ratio, whether the distress layer contributed to the downgrade.

## 5. Distress Trend and Outlook

Distress does not only affect the level of the rating; it can also influence the outlook.

After computing the base outlook from the score band, the model can adjust it based on distress notches and trends in key metrics:
```Python
hardstop_outlook = derive_outlook_with_distress_trend(
    base_outlook,
    distress_notches,
    quant_inputs.fin_t0,
    quant_inputs.fin_t1,
)
```
## High-level logic

- If `distress_notches >= 0`, the distress layer does not worsen the outlook, so `hardstop_outlook` usually equals `base_outlook`.

- If `distress_notches < 0`, the function examines trends in:

- `interest_coverage`

- `dscr`

- `altman_z`

For each metric, it compares **t0** with **t1**:

If most signals are deteriorating and none clearly improving, the outlook can be forced to **Negative**.

If there is a mixed or improving picture, the outlook can remain **Stable**, even if the hardstop downgrade is active.

This allows the model to distinguish between a **static weak** situation and a **weak but improving one**.

## 6. Scenario Overview
## Scenario A – No Distress

- `distress_notches = 0`

- `hardstop_rating = base_rating`

- `hardstop_triggered = False`

- `DistressNotches = 0` for all metrics in the log

The distress layer is inactive either because indicators are above thresholds or because hardstops are disabled.

## Scenario B – Mild Distress

Example:

- `interest_coverage` slightly below 1.0

- `dscr` slightly below 1.0

- `altman_z` above its distress thresholds

Illustrative outcome:

−2 notches from interest coverage

−1 notch from dscr

0 from altman_z

Total raw notches: −3 (above the −4 floor).

If:
```Python
base_rating = BBB
```
Then (depending on `RATING_SCALE`):

`hardstop_rating` is three notches weaker (e.g. **BB-**), and the outlook may remain **Stable** or move to **Negative** depending on trends.

## Scenario C – Severe Distress

Example:

- `interest_coverage` < 0.5

- `dscr` < 0.8

- `altman_z` < 1.2

Raw contributions might sum to more than −4 (for example −11), but:
```
total_notches is floored at MAX_DISTRESS_NOTCHES = -4
```

If:
```Python
base_rating = BBB
```

Then:

`hardstop_rating` is four notches weaker (e.g. down to the **“B” area**, depending on scale).

The downgrade is significant but still **bounded**.

## Scenario D – Improving Trend

Improving distress ratios do **not automatically remove** an active hardstop; absolute levels still determine whether thresholds are breached and whether a downgrade is applied.

However:

When hardstops have actually bitten (`distress_notches < 0`) and the sovereign cap is not binding, the outlook adjustment (`hardstop_outlook`) can differentiate between:

**Weak but improving metrics** → more likely **Stable**

**Weak and deteriorating metrics** → more likely **Negative**

Scenario E – Hardstops Disabled

If:
```python
enable_hardstops = False
```
Then:

- `distress_notches = 0`

- `hardstop_rating = base_rating`

- `hardstop_triggered = False`

- `hardstop_details = {}`

- `DistressNotches` in the ratio log remain zero

The distress layer is fully bypassed. The model then proceeds directly from the base rating to the **sovereign cap logic** (if enabled).

## 7. Interaction with Sovereign Cap

The overall rating flow is:
```
base rating → hardstop rating → sovereign-capped final rating
```
The **hardstop rating** is the starting point for the sovereign cap:

If the cap is **disabled** or **non-binding**, the final rating equals the **hardstop rating**.

If the cap is **enabled** and the sovereign rating is weaker, it constrains the issuer to be **no better than the sovereign**.

Outlook after the sovereign cap is determined by combining:

- `hardstop_outlook` (which already reflects distress and trends), and

- the **sovereign outlook**, when the cap is binding.

The hardstop layer and the sovereign cap are both optional, controlled independently by:

- `enable_hardstops`

- `enable_sovereign_cap`

## 8. Design Intent

The distress hardstop layer:

Is **non-compensatory**: sufficiently weak coverage or Altman Z cannot be fully offset by strength elsewhere.

Uses transparent, rule-based notching based on a small set of well-defined distress metrics.

Is bounded by `MAX_DISTRESS_NOTCHES` to avoid extreme downgrades from overlays.

Feeds into the outlook via trend analysis, not only into the rating level.

Is optional and can be toggled via `enable_hardstops` depending on use case and risk appetite.

In combination with the **main scoring engine** and **sovereign cap logic**, the distress overlay ensures that **near-default profiles** are consistently reflected in both the **level** and the **trajectory (outlook)** of the rating.
