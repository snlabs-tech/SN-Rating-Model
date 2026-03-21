# SN Rating Model

![Python](https://img.shields.io/badge/Python-3.x-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

## Status

This repository contains the **latest and actively maintained** SN Rating Model.
Earlier implementations of the SN Rating Model are **deprecated** and kept only
for historical reference. They will not receive new features or bug fixes.

## Overview
The **SN Rating Model** uses generic, illustrative financial ratios and scoring bands that have not been probability‑of‑default (PD) validated or approved for regulatory capital or IFRS 9/CECL use. It is intended for educational, exploratory and prototype purposes only. Users may customize the configuration and calibrate the score‑to‑PD or grade mapping to align with their own internally validated models and governance frameworks.

The project supports two main use cases:

* **Windows executable workflow** for non-technical users
* **Python package implementation** for developers and analysts

The model reads Excel input data, applies scoring rules defined in configuration files, and generates a **rating report**.

---

# Repository Structure

## Repository Structure

```
SN-Rating-Model/
├── src/
│   └── sn_rating/              # Core Python package
│       ├── __init__.py         # Marks this as a Python package; can also expose package-level metadata
│       ├── config.py           # Configuration handling
│       ├── datamodel.py        # Data structures and schemas
│       ├── excel_io.py         # Excel input logic
│       ├── helpers.py          # Utility functions
│       ├── model.py            # Rating model logic
│       ├── report.py           # Report generation helpers
│       └── run_from_excel.py   # Entry point for Excel-based runs
│
├── windows_bundle/             # Standalone Windows execution package
│   ├── run_sn_rating.bat       # Batch wrapper around the .exe
│   ├── Run_SN_RatingModel.exe  # Packaged Windows executable
│   ├── input/
│   │   ├── sn_rating_input.xlsx   # Company input template
│   │   └── sn_rating_config.xlsx  # Configuration workbook
│   └── output/                 # Created at runtime, holds rating reports
│
├── docs/                       # Methodology and workflow documentation
│   ├── Hardstop_Rating_Workflow.md
│   ├── Methodology overview.md
│   ├── Quantitative_Factors_and_Ratio_Definitions.md
│   ├── Rating–Outlook Workflow.md
│   ├── Sovereign Cap Workflow.md
│   ├── windows_bundle.md
│   └── user_manual.md
│
├── notebooks/                  # Exploratory analysis and demos
│   └── sn_rating.ipynb
│
├── requirements.txt            # Python dependencies
├── README.md                   # Main project overview and usage
├── LICENSE                     # MIT license
└── .gitignore                  # Tells Git which files/folders to ignore (e.g. venvs, outputs, temp files)
```

---

# Windows Usage (No Python Required)

The project supports a **Windows bundle workflow** that allows users to run the rating model without installing Python.

### Steps

### 1. Navigate to

```
windows_bundle/
```

### 2. Open the input file

```
input/sn_rating_input.xlsx
```

Enter the company data.

### 3. (Optional) Adjust scoring configuration

```
input/sn_rating_config.xlsx
```

This file controls:

* ratio scoring bands
* qualitative factor thresholds
* scoring directions (higher the better, lower the better)


### 4. Save and close Excel

### 5. Run the model

Double-click:

```
run_sn_rating.bat
```

### 6. View the results

After execution completes, open:

```
windows_bundle/output/
```

The folder will contain the generated **rating report**.

---

# Python Package Usage (Developers)

## Requirements

* Python 3.x
* pandas
* numpy
* openpyxl

Install any additional dependencies listed in your environment setup.

---

# Installation

Clone the repository:

```bash
git clone https://github.com/snlabs-tech/SN-Rating-Model.git
cd SN-Rating-Model
```

Install the package locally:

```bash
pip install -e .
```

---

# Running the Model

From the project root:

```bash
python -m sn_rating
```

This will execute the rating model using the Excel files located in the **windows_bundle/input** directory.

---

# Core Modules

The Python implementation is located in:

```
src/sn_rating/
```

Key components include:

### `config.py`

Handles loading and validation of configuration data from:

```
sn_rating_config.xlsx
```

---

### `model.py`

Contains the **core rating logic**, including:

* financial ratio scoring
* qualitative factor scoring
* weighted score aggregation
* final rating calculation

---

### `excel_io.py`

Responsible for:

* reading Excel inputs
* validating input structures
* exporting intermediate results if needed

---

### `report.py`

Generates the **final rating report**, typically written to the `output/` directory.

---

# Model Inputs

## Input Data

```
sn_rating_input.xlsx
```

Typical contents include:

* company metadata
* financial ratios
* qualitative factors
* peer comparison data

---

## Configuration

```
sn_rating_config.xlsx
```

Defines model parameters including:

* scoring thresholds
* scoring directions
* rating band definitions

---

# Customization

The model is designed to be **configurable via Excel**.

Users can safely adjust:

* scoring thresholds
* ratio bands
* qualitative scoring ranges

However, **structural changes** such as:

* removing required columns
* renaming sheets
* changing expected formats

may require **updates to the Python source code**.

---

# Output

After running the model, results are written to:

```
windows_bundle/output/
```
The main output is an Excel rating report that includes:
- The final alphanumeric rating (e.g. BBB, BB+) and total score
- A one‑page A4‑style summary of key ratios, qualitative factors and peer information
- A log / calculations sheet showing the detailed scoring steps used to derive the rating

---

# License

This project is licensed under the terms described in the **LICENSE** file.

---

# Maintainer

**SN Labs**

For questions, improvements, or issues, please open an issue in this repository.
