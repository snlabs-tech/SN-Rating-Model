# SN Rating Model
![Python](https://img.shields.io/badge/Python-3.x-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

## Status

This repository contains the **latest and actively maintained** SN Rating Model.  
Earlier implementations of the SN Rating Model are **deprecated** and kept only for historical reference; they will not receive new features or bug fixes.

## Overview

The **SN Rating Model** is a transparent, configurable corporate credit scoring engine that maps a 0–100 score to a rating grade from AAA to C via an Excel‑driven workflow. It uses generic, illustrative financial ratios and scoring bands that have **not** been probability‑of‑default (PD) validated or approved for regulatory capital or IFRS 9/CECL use. It is intended for educational, exploratory and prototype purposes only.

Users can adjust ratio bands and factor weights in Excel and may calibrate the score‑to‑PD or grade mapping within their own validated frameworks and governance.

The project supports two main use cases:

- **Windows executable workflow** for non‑technical users  
- **Python source workflow** for developers and analysts

The model reads Excel input data, applies scoring rules defined in configuration files, and generates an Excel **rating report**.

---

## Repository structure

```text
SN-Rating-Model/
├── windows_bundle/             # Standalone Windows execution package
│   ├── run_sn_rating.bat       # Batch wrapper around the .exe
│   ├── Run_SN_RatingModel.exe  # Packaged Windows executable
│   ├── input/
│   │   ├── sn_rating_input.xlsx   # Company info input template
│   │   └── sn_rating_config.xlsx  # Configuration workbook
│   └── output/                 # Created at runtime, holds rating reports
│
├── src/                        # Python execution package
│   ├── input/
│   │   ├── sn_rating_input.xlsx   # Company info input template
│   │   └── sn_rating_config.xlsx  # Configuration workbook
│   ├── run_sn_rating.py        # Python file for CLI run
│   ├── output/                 # Created at runtime, holds rating reports
│   └── sn_rating/              # Core Python package
│       ├── __init__.py         # Package metadata
│       ├── config.py           # Configuration handling
│       ├── datamodel.py        # Data structures and schemas
│       ├── excel_io.py         # Excel input logic
│       ├── helpers.py          # Utility functions (bands, outlook, etc.)
│       ├── model.py            # Rating model logic
│       ├── report.py           # Report generation helpers
│       └── run_from_excel.py   # Entry point for Excel-based runs
│
├── docs/                       # Methodology and workflow documentation
│   ├── 1_User_Manual.md
│   ├── 2_Running_The_Model.md
│   ├── 3_Methodology_Overview.md
│   ├── 4_Quantitative_Factors_and_Ratio_Definitions.md
│   ├── 5_Rating_Outlook_Workflow.md
│   ├── 6_Hardstop_Rating_Workflow.md
│   └── 7_Sovereign_Cap_Workflow.md
│
├── notebooks/                  # Exploratory analysis and demos
│   └── sn_rating.ipynb
│
├── requirements.txt            # Python dependencies
├── README.md                   # Main project overview and usage
├── LICENSE                     # MIT license
└── .gitignore                  # Git ignore rules
```

---

## High‑level Rating Stack

Conceptually, the model applies three layers:

1. **Base rating (unconstrained)**  
   Derived from the combined quantitative and qualitative score using `SCORE_TO_RATING`, with no distress overlay and no sovereign cap.

2. **Distress hardstops (optional)**  
   Apply notch‑down adjustments based on any ratios configured in `DISTRESS_BANDS` (e.g. interest coverage, DSCR, Altman Z, liquidity or covenant ratios). If no `distress_bands` input is provided in the Excel config, the model falls back to the three core metrics: `interest_coverage`, `dscr`, and `altman_z`.  
   The distress / hardstop mechanism acts like a configurable **covenant‑style breach trigger**: whenever any configured ratio crosses a specified distress threshold, the model applies the associated downgrade notches to the base rating, subject to `MAX_DISTRESS_NOTCHES`.

3. **Sovereign cap (optional)**  
   Ensures the final issuer rating is not better than the specified sovereign rating when the cap is enabled.

The **hardstop rating** is the outcome after applying the distress layer to the base rating. When `enable_hardstops` is `False`, the hardstop rating equals the base rating and the distress layer is effectively inactive.

Distress can also affect the **outlook** via trend‑based logic that looks at selected distress metrics over time.

For a detailed description, see `docs/6_Hardstop_Rating_Workflow.md`.

---

# Windows Usage (No Python Required)

The **Windows bundle workflow** lets you run the model without installing Python.

### 1. Navigate to the bundle

```text
windows_bundle/
```

### 2. Edit input data

Open:

```text
input/sn_rating_input.xlsx
```

and enter the company data (see `docs/1_User_Manual.md` for details on the `metadata`, `fin_ratios`, `components`, `qual_factors`, and `peers_t0` sheets).

### 3. (Optional) Adjust configuration

Open:

```text
input/sn_rating_config.xlsx
```

This workbook controls:

- Ratio scoring bands  
- Ratio/family weights  
- Scoring directions (via `higher_better` / `lower_better` config sheets, as applicable)  
- Distress bands (`distress_bands` sheet) and global options such as `MAX_DISTRESS_NOTCHES`.

### 4. Save and close Excel

Make sure both input and config workbooks are saved and closed before running the model.

### 5. Run the model

Double‑click:

```text
run_sn_rating.bat
```

This calls `Run_SN_RatingModel.exe` with the configured Excel files.

### 6. View the results

After execution completes, open:

```text
windows_bundle/output/
```

The folder will contain the generated **rating report** Excel file.

---

# Python Package Usage (Developers)

## Requirements

- Python 3.x  
- Packages listed in `requirements.txt` (e.g. `pandas`, `numpy`, `openpyxl`, `numexpr`, etc.)

Install dependencies into a virtualenv or conda env:

```bash
pip install -r requirements.txt
```

## Installation

Clone the repository:

```bash
git clone https://github.com/snlabs-tech/SN-Rating-Model.git
cd SN-Rating-Model
```

(Editable install is optional; you can also run directly from source.)

```bash
pip install -e .
```

---

## Running the Model from Source

The recommended source‑based entry point is a small script (e.g. `run_sn_rating.py`) that calls the Excel‑driven runner and writes the report to `output/`.

From the project root:

```bash
python run_sn_rating.py
```

This will execute the rating model using the Excel files in `src/input/` or `windows_bundle/input/` (depending on how `run_sn_rating.py` is configured) and write the report into an `output/` directory.

---

# Core Modules

The Python implementation lives under:

```text
src/sn_rating/
```

### `config.py`

- Loads configuration from `sn_rating_config.xlsx` or code defaults.  
- Manages:
  - `SCORE_TO_RATING` and derived `RATING_SCALE`  
  - Ratio scoring bands (`RATIOS_LOWER_BETTER`, `RATIOS_HIGHER_BETTER`)  
  - `DISTRESS_BANDS` and `MAX_DISTRESS_NOTCHES` (dynamic distress notching)  
  - Optional `DISTRESS_TREND_METRICS` for distress‑trend‑based outlook

### `model.py`

Contains the **core rating logic**, including:

- Financial ratio scoring and bucket averages  
- Qualitative factor scoring  
- Weighted score aggregation and base rating  
- Distress / hardstop notching driven by `DISTRESS_BANDS`, with fallback to the three core metrics if the config is empty  
- Peer positioning (if enabled)  
- Sovereign cap logic and final outlook computation.

### `helpers.py`

Provides utilities such as:

- `BandConfig` (band lookup and direction detection)  
- `compute_altman_z_from_components`  
- `compute_effective_weights` for quant vs qual blocks  
- `derive_outlook_band_only` (band‑based base outlook)  
- `derive_outlook_with_distress_trend` (adjusts outlook when distress is present and distress metrics are deteriorating; uses `DISTRESS_TREND_METRICS` if set, or falls back to `["interest_coverage", "dscr", "altman_z"]`).

### `excel_io.py`

Responsible for:

- Reading Excel inputs  
- Validating input structures  
- Preparing data structures used by `RatingModel`.

### `report.py`

- Generates the **final rating report** Excel workbook, typically in the `output/` directory.

### `run_from_excel.py`

Implements the Excel‑driven workflow:

- Loads configuration and input workbooks  
- Calls the rating model  
- Returns structured results that your runner (or the .exe) can write to Excel.

---

# Model Inputs

## Input Data

```text
windows_bundle/input/sn_rating_input.xlsx
```

Contains sheets such as:

- `metadata` – Company identifiers and model switches (sovereign rating/outlook, enable flags, quantitative/qualitative weights).  
- `fin_ratios` – Financial ratios or base financials used in quantitative scoring (model currently uses T0; prior years can be kept for reference).  
- `components` – Altman‑Z input components when Altman‑Z is not directly provided as a ratio.  
- `qual_factors` – 1–5 expert scores for qualitative dimensions.  
- `peers_t0` – Peer company data for T0, used for peer comparison tables.

See `docs/1_User_Manual.md` for a detailed field‑by‑field description.

## Configuration

```text
windows_bundle/input/sn_rating_config.xlsx
```

Defines model parameters including:

- Ratio scoring bands / thresholds (`lower_better` / `higher_better` sheets)  
- Ratio and family weights  
- Direction assignments (`higher_better` vs `lower_better`)  
- Distress configuration: `distress_bands` sheet defining metric‑level distress thresholds and `notches_down`, plus `MAX_DISTRESS_NOTCHES` in the `others` sheet.
  
  **Note:** The `distress_bands` sheet fully overrides the built‑in defaults; if it contains any rows, only the metrics listed there are used for distress.
  If it is missing or empty, the model falls back to the default bands for `interest_coverage`, `dscr`, and `altman_z`.
  
- Optional quantitative/qualitative global weights and other switches

The current version keeps qualitative mappings (1–5 → points) and some score→grade defaults in code rather than in Excel.

---

# Distress / Hardstops (Conceptual Summary)

- Distress bands are **dynamic**: any metric listed in `DISTRESS_BANDS` (from defaults or Excel) can trigger **covenant‑style hardstops** when its value breaches one of the configured thresholds.
- The total distress effect is aggregated into `distress_notches` and applied as a downgrade overlay to the base rating, with a floor at `MAX_DISTRESS_NOTCHES`. 
- The ratio log in the report includes a `DistressNotches` column showing, per metric, whether it contributed to the hardstop.
- Distress also feeds into the **outlook**: when `distress_notches < 0`, the model examines trends in selected distress metrics (from `DISTRESS_TREND_METRICS` or the default trio) to differentiate weak‑but‑improving from weak‑and‑deteriorating profiles.

See `docs/6_Hardstop_Rating_Workflow.md` for full details and examples.

---

# Output

For the Windows bundle, results are written to:

```text
windows_bundle/output/
```

For the Python workflow, results are written to:

```text
output/
```

(depending on how `run_sn_rating.py` is configured).

The main output is an Excel rating report that includes:

- The final alphanumeric rating (e.g. BBB, BB+) and total score  
- Outlook (e.g. Stable, Positive, Negative)  
- A one‑page A4‑style summary of key ratios and qualitative factors  
- Peer comparison tables (if peers are provided)  
- A log / calculations sheet showing the detailed scoring steps, including per‑ratio bands, weights, distress notches, and peer flags

---

# Customization

The model is designed to be **configurable via Excel** for most practical adjustments.

You can safely adjust:

- Ratio scoring bands and breakpoints  
- Ratio and category weights  
- Direction assignments for ratios (higher vs lower is better)  
- Quantitative vs qualitative block weights (in the `metadata` sheet)  
- Distress bands (`distress_bands` sheet) and `MAX_DISTRESS_NOTCHES`  
- Sovereign and peer features via TRUE/FALSE flags on `metadata`

Avoid changing:

- Sheet names  
- Required column headers  
- Expected data types and ranges

Structural changes (e.g. adding/removing sheets, changing layouts, modifying qualitative mappings or grade cutoffs) may require updates to the Python source.

---

# License

This project is licensed under the terms described in the **LICENSE** file (MIT).

---

# Maintainer

**SN Labs**

For questions, improvements, or issues, please open an issue in this repository.
