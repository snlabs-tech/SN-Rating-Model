# SN Rating Model

![Python](https://img.shields.io/badge/Python-3.x-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

The **SN Rating Model** is a financial and qualitative scoring system designed to generate structured company rating reports based on financial ratios, qualitative factors, and configurable scoring rules.

The project supports two main use cases:

* **Windows executable workflow** for non-technical users
* **Python package implementation** for developers and analysts

The model reads Excel input data, applies scoring rules defined in configuration files, and generates a **rating report**.

---

# Repository Structure

```
SN-Rating-Model/
│
├── src/
│   └── sn_rating/
│       ├── __init__.py
│       ├── config.py        # configuration loading
│       ├── model.py         # scoring logic
│       ├── excel_io.py      # Excel input/output handling
│       ├── report.py        # report generation
│       └── ...
│
├── windows_bundle/
│   ├── run_sn_rating.bat    # Windows execution script
│   │
│   ├── input/
│   │   ├── sn_rating_input.xlsx
│   │   └── sn_rating_config.xlsx
│   │
│   └── output/              # created at runtime (initially empty)
│
├── .gitignore
├── LICENSE
└── README.md
```

---

# Windows Usage (No Python Required)

The project supports a **Windows bundle workflow** that allows users to run the rating model without installing Python.

> **Pre-built Windows bundle (includes EXE):**  
> Download from Google Drive and unzip locally:  
> https://drive.google.com/drive/folders/1HO1RlAsAlyZne9zIWS3HURCssjqftpv3?usp=sharing

### Steps

### 1. Navigate to

```
windows_bundle/
```

### 2. Open the input file

```
input/sn_rating_input.xlsx
```

Enter your company data.

### 3. (Optional) Adjust scoring configuration

```
input/sn_rating_config.xlsx
```

This file controls:

* ratio scoring bands
* qualitative factor thresholds
* scoring directions
* weightings

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
* factor weights
* rating band definitions

---

# Customization

The model is designed to be **configurable via Excel**.

Users can safely adjust:

* scoring thresholds
* factor weights
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

Typical outputs include:

* rating summary
* detailed score breakdown
* generated rating report

---

# License

This project is licensed under the terms described in the **LICENSE** file.

---

# Maintainer

**SN Labs**

For questions, improvements, or issues, please open an issue in this repository.
