# SN Corporate Rating Model – User Manual

This short manual explains how to use the SN Corporate Rating Model at a practical level and points you to the detailed methodology and configuration documentation.

---

## 1. What this tool is (and is not)

- The model is a transparent, rules‑based framework that combines quantitative financial ratios and qualitative factors into an internal issuer rating and outlook.
- It is intended for educational, exploratory, and internal analytical use; it is **not** a PD‑calibrated, rating‑agency‑validated model.
- The default ratios, bands, and rating scale are **illustrative**. Users are expected to define their own configuration (ratios, bands, and score‑to‑rating scale) and validate it against their own portfolio and governance.

For the full methodology, see:  
`SN-Rating-Model/docs/2_Methodology.md`.

---

## 2. Files and folders you will touch

From the cloned repository, the key items are:

- `input/`
  - `sn_rating_input.xlsx` – main input workbook (issuer data, ratios, qualitative factors, peers, metadata).
  - `sn_rating_config.xlsx` – configuration workbook (score‑to‑rating, ratio bands, distress bands, qualitative scale, weights).

- `output/`
  - Populated at runtime with Excel rating reports (e.g. `<Issuer_Name>_Corporate_Credit_Rating_Report.xlsx`).

- `windows_bundle/`
  - For Windows users who do *not* want to install or run Python.
  - Contains its own `input/` and `output/` folders plus a batch file and `.exe` launcher.

- `run_sn_rating.py`
  - Python script entry point for running the model from the cloned repo.

---

## 3. Quick start – Python users

Use this if you are comfortable with Python and running scripts from a terminal.

### 3.1 Setup

1. Clone or download the repository.
2. (Optional) Create and activate a virtual environment.  
3. From the project root, install dependencies:

```bash
pip install -r requirements.txt
``` 

4. Prepare `input/sn_rating_input.xlsx`:
   - Fill `metadata`, `fin_ratios`, `components`, `qual_factors`, and `peers_t0` as per the methodology.

5. (Optional) Adjust `input/sn_rating_config.xlsx`:
   - `score_to_rating` – rating scale.
   - `qual_score_scale` – mapping 1–5 to 0–100.
   - `lower_better` / `higher_better` – ratio bands and directions.
   - `distress_bands` – distress thresholds.
   - `others` – `MAX_DISTRESS_NOTCHES`, `quantitative_weight`, `qualitative_weight`.

If a sheet or entry is missing, the model automatically falls back to built‑in defaults.

### 3.2 Run the model

From the project root:

```bash
python run_sn_rating.py
```

What happens:

- Inputs are read from `input/sn_rating_input.xlsx` and `input/sn_rating_config.xlsx`.
- The rating model runs using the configuration and methodology documented in the Methodology file.
- The main report is written to `output/<Issuer_Name>_Corporate_Credit_Rating_Report.xlsx`.
- Quantitative and qualitative logs for T0 are printed to the console (value, score, weight, peer info, distress notches).

For more detail on the script and workflow, see:  
`docs/Running the model.md`.

---

## 4. Quick start – Windows bundle (no Python)

Use this if you are on Windows and prefer a double‑clickable solution.

### 4.1 One‑time setup

1. In the cloned repo, open `windows_bundle/Windows bundle download.md` and follow the Google Drive link.
2. Download `Run_SN_RatingModel.exe` and copy it into the `windows_bundle` folder next to `run_sn_rating.bat`.

Folder structure:

```text
SN-Rating-Model/
├── windows_bundle/
│   ├── run_sn_rating.bat
│   ├── Run_SN_RatingModel.exe
│   ├── input/
│   │   ├── sn_rating_input.xlsx
│   │   └── sn_rating_config.xlsx
│   └── output/
```

### 4.2 Prepare inputs

1. Open `windows_bundle/input/sn_rating_input.xlsx` and fill in the same sheets as for the Python run (`metadata`, `fin_ratios`, `components`, `qual_factors`, `peers_t0`).
2. (Optional) Adjust `windows_bundle/input/sn_rating_config.xlsx` if you want to override the default configuration.

### 4.3 Run the model

1. Double‑click `run_sn_rating.bat` inside `windows_bundle` (or run it from Command Prompt).
2. The batch file will call `Run_SN_RatingModel.exe`, which:
   - Reads the Excel inputs from `windows_bundle/input/`.
   - Runs the same methodology as the Python script.
   - Writes the Excel rating report into `windows_bundle/output/`.

Open the report in `windows_bundle/output/` to view the results.

---

## 5. Understanding and customising the model

If you plan to use the tool beyond a one‑off demo, you should review and likely customise:

- **Ratios used** (which metrics appear in `fin_ratios` and `peers_t0`).
- **Ratio bands and directions** (`lower_better` / `higher_better` sheets in `sn_rating_config.xlsx`).
- **Qualitative scale and factor definitions** (`qual_score_scale` and `qual_factors` sheet).
- **Score‑to‑rating scale** (`score_to_rating` in `sn_rating_config.xlsx`).
- **Weights and distress limits** (`quantitative_weight`, `qualitative_weight`, `MAX_DISTRESS_NOTCHES` in `others`).

The detailed logic for each of these is documented in:  
`docs/SN Corporate Rating Model – Methodology.md` (see the “Configuration methodology” section).

---

## 6. Where to find more detail

- **Methodology and configuration**  
  `docs/SN Corporate Rating Model – Methodology.md` – full description of inputs, configuration, quantitative and qualitative blocks, distress/hardstops, sovereign cap, and rating/outlook derivation.

- **How to run the model**  
  `docs/Running the model.md` – step‑by‑step instructions for:
  - Running via Python (`run_sn_rating.py`).  
  - Running via the Windows bundle (`run_sn_rating.bat` + `Run_SN_RatingModel.exe`).

Use this User Manual as your high‑level guide; consult the Methodology and Running documents when you need technical or configuration details.
```
