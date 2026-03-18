# Quantitative Factors and Ratio Definitions
> ⚠️ Disclaimer  
> The quantitative factors and ratio definitions in this document are **illustrative** and have **not** been probability‑of‑default (PD) validated or approved for regulatory capital, IFRS 9 or CECL purposes.  
> They are intended to demonstrate the model’s mechanics and are not a recommendation to use any specific ratio set in production.  
> Users should adapt the ratio set and calibrate score‑to‑PD or grade mappings to align with their own internally validated models, data, and governance frameworks.

All ratios are ultimately mapped to a 0–100 internal score using the band tables in `sn_rating_config.xlsx` (loaded via `BandConfig`). For each ratio, bands are defined such that more favourable values (for that specific ratio) receive higher scores – whether that means a higher or a lower numeric value.

---

## Leverage ratios

### `debt_ebitda` — Debt / EBITDA

- **Category**: Leverage  
- **Definition**: Total debt divided by EBITDA (earnings before interest, taxes, depreciation, and amortization).  
- **Why it matters**: Indicates how many years of current EBITDA would be needed to repay total debt; higher values signal higher leverage and weaker debt capacity.
- **Model scoring**:  
  - Scored using the bands configured for `debt_ebitda` in `sn_rating_config.xlsx`; lower leverage bands receive higher scores, higher leverage bands receive lower scores.

---

### `net_debt_ebitda` — Net Debt / EBITDA

- **Category**: Leverage  
- **Definition**: Net debt (debt minus cash and cash‑equivalents) divided by EBITDA.  
- **Why it matters**: Adjusts gross leverage for available cash; more refined than `debt_ebitda` in cash‑rich or cash‑poor situations. 
- **Model scoring**:  
  - Scored using the configured `net_debt_ebitda` bands; lower net leverage bands map to higher scores, reflecting stronger balance sheets.

---

### `ffo_debt` — FFO / Debt

- **Category**: Leverage (cash‑flow based)  
- **Definition**: Funds from operations (FFO) divided by total debt.  
- **Why it matters**: Measures recurrent cash‑flow capacity to service and repay debt; higher ratios indicate stronger deleveraging capacity.
- **Model scoring**:  
  - Scored via the `ffo_debt` bands; higher FFO/debt ranges receive higher scores, signalling stronger solvency.

---

### `fcf_debt` — FCF / Debt

- **Category**: Leverage (cash‑flow based)  
- **Definition**: Free cash flow (after capex and working capital) divided by total debt.  
- **Why it matters**: Captures the issuer’s ability to reduce debt from discretionary cash flow after investments; persistent negative values are a warning signal.
- **Model scoring**:  
  - Scored via the `fcf_debt` bands; sustained positive FCF/debt bands receive higher scores, negative bands receive lower scores.

---

### `debt_equity` — Debt / Equity

- **Category**: Leverage (capital structure)  
- **Definition**: Total debt divided by total equity.  
- **Why it matters**: Measures the balance between debt and equity funding; higher values mean thinner equity buffers and higher financial risk. 
- **Model scoring**:  
  - Scored via `debt_equity` bands; lower debt/equity ranges are mapped to higher scores.

---

### `debt_capital` — Debt / (Debt + Equity)

- **Category**: Leverage (capital structure)  
- **Definition**: Total debt divided by total capital (debt plus equity).  
- **Why it matters**: Alternative leverage measure; higher ratios indicate more debt‑heavy capital structures and less loss‑absorbing equity.  
- **Model scoring**:  
  - Scored via `debt_capital` bands; lower debt-to-capital ranges receive higher scores.

---

## Coverage ratios

### `interest_coverage` — EBITDA / Interest (or similar)

- **Category**: Coverage  
- **Definition**: Earnings (EBITDA or EBIT, depending on definition) divided by interest expense.  
- **Why it matters**: Indicates the headroom to service interest from recurring earnings; low values are a classic distress signal and feed into both scoring and hardstop logic. 
- **Model scoring**:  
  - Scored via `interest_coverage` bands; higher coverage bands receive higher scores.

---

### `fixed_charge_coverage` — Fixed‑Charge Coverage

- **Category**: Coverage  
- **Definition**: Earnings relative to all fixed charges (interest plus lease payments, etc.).  
- **Why it matters**: Broadens coverage beyond pure interest to include other fixed financial commitments.  
- **Model scoring**:  
  - Scored via `fixed_charge_coverage` bands; stronger coverage ranges map to higher scores.

---

### `dscr` — Debt Service Coverage Ratio

- **Category**: Coverage  
- **Definition**: Cash flow available for debt service divided by total debt service (interest + principal repayments).  
- **Why it matters**: Direct measure of short‑term debt service capacity; low DSCR triggers distress notching in addition to weaker scores.
- **Model scoring**:  
  - Scored via `dscr` bands; higher DSCR bands receive higher scores.

---

## Profitability and return ratios

### `ebitda_margin` — EBITDA Margin

- **Category**: Profitability  
- **Definition**: EBITDA divided by revenue.  
- **Why it matters**: Captures operating profitability and buffer against shocks; higher margins typically support better ratings. 
- **Model scoring**:  
  - Scored via `ebitda_margin` bands; higher margin ranges map to higher scores.

---

### `ebit_margin` — EBIT Margin

- **Category**: Profitability  
- **Definition**: EBIT divided by revenue.  
- **Why it matters**: Profitability after depreciation and amortisation; often more conservative than EBITDA margin and informative in capital‑intensive sectors.  
- **Model scoring**:  
  - Scored via `ebit_margin` bands; higher EBIT margin bands receive higher scores.

---

### `roa` — Return on Assets

- **Category**: Profitability / efficiency  
- **Definition**: Net income divided by total assets.  
- **Why it matters**: Indicates efficiency in generating profits from the asset base; persistently low ROA may signal weak business models or over‑investment.
- **Model scoring**:  
  - Scored via `roa` bands; higher ROA ranges map to higher scores.

---

### `roe` — Return on Equity

- **Category**: Profitability / equity return  
- **Definition**: Net income divided by equity.  
- **Why it matters**: Measures returns for shareholders; very low or negative ROE may indicate structural issues; extremely high ROE can also signal leverage. 
- **Model scoring**:  
  - Scored via `roe` bands; sustainable, robust ROE bands receive higher scores, weak or negative ranges receive lower scores.

---

## Investment and liquidity ratios

### `capex_dep` — Capex / Depreciation

- **Category**: Investment intensity  
- **Definition**: Capital expenditure divided by depreciation expense.  
- **Why it matters**: Indicates whether the issuer is under‑investing (capex below depreciation) or aggressively expanding (very high capex); both extremes can carry risk.
- **Model scoring**:  
  - Scored via `capex_dep` bands; the bands can be configured to favour a “sustainable investment” zone (e.g. around replacement levels) and penalise both under‑ and over‑investment if desired.

---

### `current_ratio` — Current Assets / Current Liabilities

- **Category**: Liquidity  
- **Definition**: Current assets divided by current liabilities.  
- **Why it matters**: Measures short‑term liquidity; very low values signal refinancing pressure, very high values may signal inefficient capital allocation. 
- **Model scoring**:  
  - Scored via `current_ratio` bands; ratios that indicate comfortable, but not excessive, liquidity receive higher scores.

---

### `rollover_coverage` — Rollover Coverage

- **Category**: Liquidity / refinancing  
- **Definition**: Cash plus committed undrawn lines relative to short‑term debt maturities (or similar proxy).  
- **Why it matters**: Captures near‑term refinancing risk; low values signal vulnerability to market closures or failed refinancing.
- **Model scoring**:  
  - Scored via `rollover_coverage` bands; higher coverage of near‑term maturities maps to higher scores.

---

## Distress indicator

### `altman_z` — Altman Z‑score

- **Category**: Distress / solvency  
- **Definition**: Linear combination of working capital, retained earnings, EBIT, market value of equity, and sales, each scaled by assets or liabilities, per the classic Altman Z model (A–E components).
- **Why it matters**: Summarises default risk based on a set of accounting ratios; low Z‑scores are strongly associated with financial distress. 
- **Model use**:  
  - Scored via the `altman_z` bands within `BandConfig` into the relevant bucket.  
  - Also used in `DISTRESS_BANDS["altman_z"]` to drive hardstop notching when the Z‑score falls into distress territory.  

The model ensures that `altman_z` is present by computing it from its components when not directly supplied.

---

## Missing data and flexibility

The quantitative block is tolerant to missing data:

- If a ratio is not provided or has no configured bands in `BandConfig`, it is skipped.  
- The aggregate quantitative score is computed from the remaining valid ratios and the peer score (if enabled).  
- The number of valid quantitative items is tracked and used in `compute_effective_weights` to derive the relative weight of the quantitative block vs the qualitative block.

Bands for each ratio are defined in `sn_rating_config.xlsx` and can be customised to reflect sector‑specific norms, internal appetite, or empirical rating benchmarks.

---
## Ratio weights

In addition to the band definitions, each quantitative ratio can be assigned a **weight** in the `fin_ratios` sheet:

- The `weight` column allows the user to emphasise or de‑emphasise specific ratios within the quantitative block (default weight is 1.0 if left blank).  
- In `compute_quantitative`, each ratio’s 0–100 band score is multiplied by its weight, and the quantitative score is the weighted average across all included ratios (plus the peer score if enabled).  
- This lets users reflect sector‑specific priorities (for example, giving more weight to coverage ratios in highly leveraged industries, or to liquidity metrics for issuers with large near‑term maturities).
