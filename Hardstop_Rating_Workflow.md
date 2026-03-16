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

