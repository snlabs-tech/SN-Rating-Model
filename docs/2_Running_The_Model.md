# Running the model

This document explains how to run the SN-Rating-Model, either using Python from the cloned repository or using the Windows bundle for non‑technical users.

---

## 1. Running with Python (cloned repo)

This option is intended for users who are comfortable with Python and have a working Python environment.

### 1.1 Prerequisites

1. Clone or download the SN‑Rating‑Model repository.
2. Create and activate a Python environment (optional but recommended).  
3. Install dependencies from the project root:

```bash
pip install -r requirements.txt
```

4. Ensure your input workbooks are in the `input` folder at the project root:

- `input/sn_rating_input.xlsx`  
- `input/sn_rating_config.xlsx` (optional – overrides built‑in defaults)

### 1.2 Standard run via script

From the project root, run:

```bash
python run_sn_rating.py
```

This script:

1. Calls `run_from_excel_with_bands()` to:
   - Read `sn_rating_input.xlsx` and `sn_rating_config.xlsx` from the `input` folder.
   - Build the configuration (including ratio bands, distress bands, qualitative scale, score‑to‑rating scale).
   - Run the `RatingModel` and produce a `RatingOutputs` object.

2. Calls `generate_corporate_rating_report(res)` to create a formatted Excel report in the `output` folder, with a filename such as:

```text
output/<Issuer_Name>_Corporate_Credit_Rating_Report.xlsx
```

3. Prints to the console:
   - A quantitative ratio log (T0) with value, score, weight, peer average/flag, and distress notches per metric.
   - A qualitative factor log (T0), if present, with value, score, weight, and bucket.

### 1.3 Advanced usage (importing the model)

You can also run the same workflow from your own Python code (e.g. a notebook):

```python
from sn_rating.run_from_excel import run_from_excel_with_bands
from sn_rating.report import generate_corporate_rating_report

res = run_from_excel_with_bands()
out_file = generate_corporate_rating_report(res)

print("Final rating:", res.final_rating, "Final outlook:", res.final_outlook)
print("Report written to:", out_file)
```

This uses exactly the same Excel inputs, configuration, and methodology as the script.

---

## 2. Running with the Windows bundle (no Python required)

This option is intended for non‑Python or less technical users on Windows. It uses a packaged executable and a batch file to run the same model without requiring Python to be installed.

### 2.1 Windows bundle folder structure

In the cloned repository, the Windows bundle lives under `windows_bundle/`:

```text
SN-Rating-Model/
├── windows_bundle/             # Standalone Windows execution package
│   ├── run_sn_rating.bat       # Batch wrapper around the .exe
│   ├── Run_SN_RatingModel.exe  # Packaged Windows executable (to be downloaded)
│   ├── input/
│   │   ├── sn_rating_input.xlsx   # Company info input template
│   │   └── sn_rating_config.xlsx  # Configuration workbook (optional overrides)
│   └── output/                 # Created at runtime, holds rating reports
```

### 2.2 Downloading the executable

1. Open `windows_bundle/Windows bundle download.md` in the repository.  
2. Follow the Google Drive link provided there and download `Run_SN_RatingModel.exe`.  
3. Place `Run_SN_RatingModel.exe` inside the `windows_bundle` folder, next to `run_sn_rating.bat`.

### 2.3 Preparing inputs (Excel files)

1. Open `windows_bundle/input/sn_rating_input.xlsx` and fill in:
   - `metadata`, `fin_ratios`, `components`, `qual_factors`, and `peers_t0` as described in the Methodology document.

2. (Optional) Open `windows_bundle/input/sn_rating_config.xlsx` to:
   - Adjust `score_to_rating`, `qual_score_scale`, `lower_better`, `higher_better`, `distress_bands`, and `others` according to your internal methodology.
   - If this workbook or some sheets/cells are left blank, the model uses the built‑in defaults for those parts of the configuration.

### 2.4 Running the model on Windows

1. In Windows Explorer, double‑click `run_sn_rating.bat` inside the `windows_bundle` folder, or run it from a Command Prompt.  
2. The batch file will:
   - Invoke `Run_SN_RatingModel.exe`.
   - Read input and configuration from `windows_bundle/input/`.
   - Execute the same rating methodology as the Python script.
   - Write the Excel rating report to `windows_bundle/output/`.

The main output is an Excel workbook named similar to:

```text
windows_bundle/output/<Issuer_Name>_Corporate_Credit_Rating_Report.xlsx
```

You can open this file in Excel to review the rating, outlook, peer positioning, and detailed logs.

---

## 3. Methodology consistency

Regardless of how you run the model:

- Python script (`python run_sn_rating.py` in the cloned repo), or  
- Windows bundle (`run_sn_rating.bat` + `Run_SN_RatingModel.exe`),

the underlying methodology is identical and is fully described in the *SN Corporate Rating Model – Methodology* document. Both paths:

- Read inputs from an Excel workbook (`sn_rating_input.xlsx`).  
- Read configuration from `sn_rating_config.xlsx` (overriding built‑in defaults where provided).  
- Use the same quantitative, qualitative, distress, peer, and sovereign‑cap logic.  
- Produce the same style of Excel rating report in an `output` folder.
```
