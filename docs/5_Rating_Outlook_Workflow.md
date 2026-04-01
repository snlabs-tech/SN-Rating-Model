# Rating–Outlook Workflow

This document explains how the model determines the **rating outlook** (Positive / Stable / Negative), given the different layers of logic: the score band, the optional distress hardstops, and the optional sovereign cap.

The key idea is: *the outlook is driven by the same mechanism that effectively constrains the rating* (pure score, distress, or sovereign).

---

## 1. Building Blocks

### 1.1 Combined Score and Base Rating Band

From the quantitative and qualitative blocks, the model computes:

- `combined_score` (0–100)  
- `base_rating` via `SCORE_TO_RATING` (e.g. 55.5 → BBB)

Each rating grade has a numeric **band** `[band_min, band_max]` in score space (e.g. BBB = 55–59).

`derive_outlook_band_only(combined_score, rating)`:

1. Looks up the band for `rating`.  
2. Floors the combined score: `cs = floor(combined_score)`.  
3. Maps position to outlook:
   - `cs == band_max` → **Positive**
   - `cs == band_min` → **Negative**
   - Otherwise → **Stable**

So within a given rating grade, the bottom of the band is Negative, the top is Positive, and the middle is Stable.

In the current implementation the **base outlook** is always derived from the **base_rating** and `combined_score` (before hardstops and cap).

---

### 1.2 Distress Hardstops and Trends

The rating‑outlook logic is driven primarily by financial‑distress indicators and their trends over time. This workflow is split into two stages:

1. **1.2 Distress hardstops**

The engine uses three quantitative distress indicators:
- `interest_coverage`
- `dscr` (debt‑service coverage ratio)
- `altman_z`

At each rating run, the function `compute_distress_notches(fin_t0, altman_z)` is called to apply the distress‑hardstop logic:

- For each metric, the engine checks whether its value falls below its corresponding threshold bands in `DISTRESS_BANDS`.  
- For every metric that breaches its band, the engine assigns a negative “notch” value (e.g., −1, −2) and sums these notches.  
- The total is then floored at `MAX_DISTRESS_NOTCHES` (a configurable negative cap) to prevent unduly aggressive downgrades.  
- The function returns:
  - `distress_notches` (total negative notches),
  - `hardstop_details` (per‑metric breakdown of which bands were breached), and
  - `per_metric_notches` (notches assigned to each individual metric).

2. **Distress‑driven trend overlay**

The trend‑sensitive outlook step only activates when distress hardstops have actually bitten, i.e., when `distress_notches < 0`:

```python
derive_outlook_with_distress_trend(base_outlook, distress_notches, fin_t0, fin_t1)
```

- If `distress_notches >= 0` (no active distress), the outlook remains exactly `base_outlook`; no trend‑based adjustment is applied.  
- If `distress_notches < 0` (distress active), the engine compares `t1 → t0` for `interest_coverage`, `dscr`, and `altman_z`:

  - For each metric that has values in both periods:
    - If `t0 > t1` → the metric is **improving**.
    - If `t0 < t1` → the metric is **deteriorating**.

Then the following rules are applied:

- **Improving and not deteriorating** (all tracked distress metrics are improving or flat) → **Stable** outlook.  
- **Deteriorating and not improving** (any metric is deteriorating and none are clearly improving) → **Negative** outlook.  
- **Mixed or flat** (some metrics improving, some deteriorating, or broadly flat) → default to **Stable**.

#### Important constraints

- The trend overlay **cannot** create a **Positive** outlook; it only modifies `base_outlook` between **Stable** and **Negative**, and only when distress‑hardstops have bitten.  
- The underlying distress bands (`DISTRESS_BANDS`) are dynamic and can be extended beyond the current three ratios; the code is designed to accommodate additional distress metrics in the future while preserving this two‑stage (hardstop + trend) logic.
---

### 1.3 Sovereign Cap and Binding Definition

If enabled, the sovereign cap ensures the issuer is not rated above the sovereign on the internal scale.

`apply_sovereign_cap(hardstop_rating, sovereign_rating)` returns the worse of the two ratings according to `RATING_SCALE`.

After applying hardstops (if any), the model computes:

```python
capped_rating = hardstop_rating
if enable_sovereign_cap and sovereign_rating is not None:
    capped_rating = apply_sovereign_cap(hardstop_rating, sovereign_rating)

final_rating = capped_rating
```

The cap is considered binding if:

```python
sovereign_cap_binding = (
    enable_sovereign_cap
    and sovereign_rating is not None
    and final_rating == sovereign_rating
)
```

Binding means the final rating sits at the sovereign level under an active cap (either because the issuer was above and got cut down, or because it is exactly at the sovereign ceiling).

---

## 2. Outlook Decision Ladder

The model uses the following ladder to determine the final outlook.

---

### 2.1 Base Outlook from the Base Rating Band

First, the model derives a band-based base outlook:

```python
base_outlook, band_position = derive_outlook_band_only(
    combined_score,
    base_rating
)
```

This uses the base (unconstrained) rating and places the combined score within that band to get Positive / Stable / Negative.

---

### 2.2 Distress Trend Overlay

Next, the model applies the distress trend overlay to get the hardstop outlook:

```python
hardstop_outlook = derive_outlook_with_distress_trend(
    base_outlook,
    distress_notches,
    quant_inputs.fin_t0,
    quant_inputs.fin_t1,
)
```

If `distress_notches >= 0` (no distress downgrade), `hardstop_outlook = base_outlook`.

If `distress_notches < 0`, the outlook can move between Stable and Negative depending on whether distress metrics are improving or deteriorating, but it never becomes Positive solely due to distress logic.

At this point the model has:

- `hardstop_rating` (after distress notches)
- `hardstop_outlook` (after distress trend overlay)

---

### 2.3 Sovereign-Binding Branch

If the sovereign cap is binding and a valid sovereign outlook is provided, the model adjusts the outlook:

```python
if (
    sovereign_cap_binding
    and sovereign_outlook in {"Positive", "Stable", "Negative"}
):
    sr = sovereign_rating
    so = sovereign_outlook
    severity = {"Positive": 0, "Stable": 1, "Negative": 2}

    if is_stronger(hardstop_rating, sr):
        outlook = so
    else:
        if sr == hardstop_rating:
            candidates = [hardstop_outlook, so]
            outlook = max(candidates, key=lambda o: severity[o])
        
else:
    outlook = hardstop_outlook
```

Interpretation:

- If the sovereign cap is binding and the **issuer’s hardstop rating is stronger than the sovereign rating**, the issuer’s outlook is **capped at the sovereign outlook** (the final outlook equals `sovereign_outlook`).

- If the sovereign cap is binding and the **sovereign and issuer hardstop ratings are equal**, the model takes the **more conservative (more negative) outlook** between:
  - `hardstop_outlook`
  - `sovereign_outlook`

- If the sovereign cap is binding and the **sovereign rating is weaker than the issuer’s hardstop rating**, or if the cap is not binding / sovereign outlook is invalid, the final outlook **remains driven by the issuer’s distress logic** (`hardstop_outlook`).
---

### 2.4 AAA Guardrail

Finally the model applies a guardrail:

```python
if final_rating == "AAA" and outlook == "Positive" and not sovereign_cap_binding:
    outlook = "Stable"
```

The model does not allow **AAA / Positive** when the rating is not sovereign-constrained, since the rating is already at the top of the scale.

---

## 3. Scenario Summary

### Scenario A – Hardstops OFF, Sovereign Cap OFF

```
enable_hardstops = False
enable_sovereign_cap = False
```

Effects:

- `distress_notches = 0`
- `hardstop_rating = base_rating`
- `hardstop_outlook = base_outlook`
- `sovereign_cap_binding = False`

Final outlook = **base_outlook**.

---

### Scenario B – Hardstops ON, No Distress, Cap OFF / Non-Binding

```
enable_hardstops = True
distress_notches >= 0
```

Effects:

- Hardstop layer does not change the rating.
- Distress trend overlay returns `base_outlook`.

Final outlook = **base_outlook**.

---

### Scenario C – Hardstops ON, Distress Deteriorating

```
enable_hardstops = True
distress_notches < 0
distress metrics deteriorating
sovereign cap not binding
```

Effects:

- `hardstop_rating` weaker than `base_rating`
- `hardstop_outlook = Negative`

Final outlook = **Negative**.

Interpretation: distress exists and is worsening.

---

### Scenario D – Hardstops ON, Distress Improving or Mixed

```
enable_hardstops = True
distress_notches < 0
metrics improving or mixed
```

Effects:

- `hardstop_rating` weaker than `base_rating`
- `hardstop_outlook = Stable`

Final outlook = **Stable**.

Interpretation: still distressed but not deteriorating.

---

### Scenario E – Sovereign Cap ON and Binding

```
enable_sovereign_cap = True
sovereign_cap_binding = True
```

Effects:
- If hardstop stronger than sovereign  → outlook aligns to sovereign outlook.
- If ratings equal → take the **more conservative outlook**.
- If hardstop weaker than sovereign → outlook driven by `hardstop_outlook`.

---

### Scenario F – Sovereign Cap ON but Not Binding

```
enable_sovereign_cap = True
sovereign_cap_binding = False
```

Effects:

- `final_rating = hardstop_rating`
- `final_outlook = hardstop_outlook`

Issuer fundamentals drive the outlook.

---

## 4. Design Intent (Intuitive Summary)

### Pure Score Environment
No distress and no sovereign constraint.

Outlook depends solely on **position in the rating band**.

- Top of band → Positive  
- Middle → Stable  
- Bottom → Negative

---

### Distress Environment
Hardstops are active but the sovereign cap does not bind.

Outlook cannot be optimistic:

- Improving / mixed distress → Stable
- Deteriorating distress → Negative

Positive outlooks are not allowed while distress notches are active.

---

### Sovereign-Constrained Environment

When the sovereign cap binds, the sovereign rating and outlook become the **effective anchor** for the issuer outlook, with conservative tie-breaking rules.

---

This structure keeps the outlook consistent with the main driver of the rating in each situation: **score position, distress overlay, or sovereign ceiling**.
