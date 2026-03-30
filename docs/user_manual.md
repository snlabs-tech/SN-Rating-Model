# SN Rating Model – User Manual

This guide explains how to use the SN Rating Model end‑to‑end, from editing the two Excel files to running the engine and reading the output.

---

## 1. Files and folders

From the repository root, the key folders and files are:

- `windows_bundle/`  
  Self‑contained folder for running the model on Windows without installing Python.

- `windows_bundle/input/sn_rating_input.xlsx`  
  Data input template (company metadata, financial ratios, qualitative factors, peers).

- `windows_bundle/input/sn_rating_config.xlsx`  
  Configuration template (ratio bands, score, factor weights, directions).

- `windows_bundle/Run_SN_RatingModel.exe`  
  Windows executable that runs the SN Rating Model engine (used by the `.bat` file).

- `windows_bundle/run_sn_rating.bat`  
  Batch script that calls `Run_SN_RatingModel.exe` with the bundled input and config files.

- `windows_bundle/output/`  
  Created at runtime; contains the generated rating report when you run the `.exe`.

If you run the model via Python source instead of the Windows bundle, you will typically use a small runner script such as:

- `run_sn_rating.py` (at repo root or under `src/`)  
  Python script that imports `sn_rating.run_from_excel.run_from_excel_with_bands(...)`, then writes the Excel report to an `output/` folder.

---

## 2. End‑to‑end workflow (Python source)

This assumes you have a conda/virtualenv with the required packages installed and a runner script `run_sn_rating.py` that calls the model and writes the Excel.

1. Create/activate your environment and install dependencies (for example via `requirements.txt`).
2. From the repo root, open `src/input/sn_rating_input.xlsx` and enter your company data (see section 4).
3. Optionally open `src/input/sn_rating_config.xlsx` to customize ratio bands, weights and other settings (see section 5).
4. Save and close both Excel files.
5. From the repo root (or `src/`, depending on where you place the script), run:
   ```bash
   python run_sn_rating.py
   ```
6. After the script finishes, open the output/ folder (where `run_sn_rating.py` writes) and inspect the generated rating report Excel file.
The exact output path and file name are defined in run_sn_rating.py (for example, `./output/<issuer_id>_<issuer_name>_Corporate_Credit_Rating_Report.xlsx`).

---

## 3. End-to-end workflow (Windows bundle, no Python install)

If you prefer the packaged Windows bundle:

1. Navigate to `windows_bundle/`.
2. Open `input/sn_rating_input.xlsx` and enter your company data (section 4).
3. Optionally edit `input/sn_rating_config.xlsx` to adjust bands, weights, and other settings (section 5).
4. Save and close both Excel files.
5. Double-click `run_sn_rating.bat` (this calls `Run_SN_RatingModel.exe`).
6. When it finishes, open `windows_bundle/output/` and view the generated rating report workbook.

---

## 4. Editing `sn_rating_input.xlsx` (company data)

This file, organised into several sheets, holds case-specific data: everything that changes from company to company.  

### 4.1 Sheet overview

Typical sheets in the input workbook:

- `metadata` – Company profile and high-level model switches  
- `fin_ratios` – Financial ratios (or base financials) for quantitative scoring  
- `components` – Input fields used to calculate the Altman‑Z score when the Altman‑Z ratio itself is not provided  
- `qual_factors` – 1–5 expert scores for qualitative dimensions  
- `peers_t0` – Peer company data for the current horizon (T0)  

> The exact sheet names/layout should be kept as in the template.

---

### 4.2 `metadata` – company info and model switches

This sheet holds identifiers and fields that affect the rating logic.

**Typical fields:**

- `name`, `id`, `country` – Company identifiers  
- `sovereign_rating`, `sovereign_outlook` – Country reference  
- `enable_peer_positioning`, `enable_hardstops`, `enable_sovereign_cap` – Feature flags (TRUE/FALSE)  


**Edit:**

- Set `name`, `id`, `country`
- Provide `sovereign_rating` and `sovereign_outlook`
- Set `enable_*` flags (`TRUE` / `FALSE`)


**Effect:**

- Drives report labelling.
- Controls caps, hard‑stops and peer features.
- If the enable_* flags are left blank, the corresponding features are ignored and treated as FALSE by default.

---

### 4.3 `fin_ratios` – financial ratios

This sheet contains numeric inputs for the quantitative block.

**Edit:**

- Fill in ratio values (or base financials) for T0 (current year).
- You can optionally maintain T1, T2 (prior years such as FY2024, FY2023) for your own reference, but the model currently uses only T0 in the rating calculation.

**Effect:**

- Drives the quantitative score  
- Ratios are mapped to bands and aggregated via weights  

---

### 4.4 `components` – Altman‑Z inputs

This sheet holds the input items needed to calculate the Altman‑Z score when the Altman‑Z ratio itself is not supplied on `fin_ratios`.

**Edit:**

- Enter the individual financial statement items required by the Altman‑Z formula (e.g. working capital, retained earnings, EBIT, market value of equity, total assets, total liabilities) when you do not provide a pre‑computed Altman‑Z ratio.

**Effect:**

- If Altman‑Z is missing on `fin_ratios`, the model uses these components to compute Altman‑Z internally.
- If Altman‑Z is already provided on `fin_ratios`, the `components` sheet is ignored for that ratio.


### 4.5 `qual_factors` – qualitative assessments (1–5)

Typical dimensions:

- Industry risk  
- Market position  
- Revenue diversification and stability  
- Business model resilience  
- Management quality and governance  
- Financial policy  
- Sovereign / legal environment  
- Transparency and information quality  

**Edit:**

- Enter scores from 1 (low) to 5 (high)

**Effect:**

- Drives qualitative scoring block  
- Impact controlled by `qualitative_weight`  

---

### 4.6 `peers_t0` – peer comparisons

**Edit:**

- Enter peer names and ratios for T0

**Effect:**

- Used for comparison tables in the report  
- Does not affect rating unless extended in code  

---

### 4.7 What not to change

To avoid breaking the model:

- Do not modify sheet names  
- Do not modify column headers  
- Do not change layout or structure  

---

## 5. Editing `sn_rating_config.xlsx` (model configuration)

This file controls model behavior without changing Python code.

---

### 5.1 Ratio scoring bands (thresholds)

**Edit:**

- Update numeric breakpoints / bands for each ratio.

**Effect:**

- Changes how ratio values map to scores.
- Only ratios that have bands defined here are considered in the model; any ratio present in the input but missing bands in the config is ignored.

---

### 5.2 Ratio and factor weights

**Edit:**

- Adjust weights for individual ratios or ratio categories/families.

**Effect:**

- Changes each metric’s contribution to the quantitative score and, via the quantitative block weight, to the final rating.

---

### 5.3 Scoring directions

**Edit:**

- Place each ratio in the appropriate direction sheet (for example `higher_better` or `lower_better`), according to whether higher or lower values are preferable.

**Effect:**

- Ensures the model interprets each ratio correctly (e.g. higher coverage is good, higher leverage is bad).
- If a ratio is not assigned to the correct direction sheet, it will not be scored as intended and may be ignored by the model.

---

### 5.4 Qualitative mappings (1–5 → points)

- Defined in Python (not editable in Excel)

**Effect:**

- Mapping is fixed, but impact is controlled via weights  

---

### 5.5 Rating band definitions (score → grade)

- Defined in Python (not editable in Excel)

**Effect:**

- Grade thresholds are fixed  

---

### 5.6 What not to change

- Sheet names  
- Column headers  
- Data types  

---

## 6. Feature-by-feature: what to edit

### 6.1 Change how ratios influence the rating

- Edit ratio bands and weights in `sn_rating_config.xlsx`

**Effect:**  
Changes sensitivity to financial metrics  

---

### 6.2 Change quantitative vs qualitative balance

- Edit `quantitative_weight` and `qualitative_weight` in `metadata`

**Effect:**  
Shifts importance between financials and qualitative inputs  

---

### 6.3 Toggle model features

- Edit:
  - `enable_hardstops`
  - `enable_sovereign_cap`
  - `enable_peer_positioning`

**Effect:**  
Activates or deactivates those mechanisms  

---

### 6.4 Reuse configuration for another company

- Update only `sn_rating_input.xlsx`
- Leave config unchanged

**Effect:**  
Same methodology applied to a new company  

---

## 7. Summary

- `sn_rating_input.xlsx` → company-specific data  
- `sn_rating_config.xlsx` → model methodology  

Run either:

```bash
python run_sn_rating.py
```
