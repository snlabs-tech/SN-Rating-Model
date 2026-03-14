# SN Rating Model

The **SN Rating Model** is an open‑source, transparent corporate credit scoring tool.  
It maps a 0–100 internal score to an alphabetic grade (AAA–CCC) using a combination of:

- Quantitative block based on financial ratios  
- Qualitative block based on 1–5 expert assessments  
- Optional peer positioning and simple sovereign / hard‑stop overlays

This model is intended for educational and exploratory use only, **not** for regulatory capital or official rating agency work.[page:1]

---

## Features

- Excel‑driven inputs (company metadata, financial ratios, qualitative factors, peers)  
- Configurable bands and thresholds via `sn_rating_config.xlsx`  
- A4 rating report generated as an Excel file  
- Open configuration philosophy: users may modify config and templates as they wish (subject to structure consistency)

---

## Repository structure

```text
SN-Rating-Model/
├── src/
│   └── sn_rating/
│       ├── __init__.py
│       ├── config.py
│       ├── model.py
│       ├── excel_io.py
│       ├── report.py
│       └── ...
├── windows_bundle/
│   ├── run_sn_rating.bat
│   ├── input/
│   │   ├── sn_rating_input.xlsx
│   │   └── sn_rating_config.xlsx
│   └── output/      # created at runtime, initially empty
├── .gitignore
├── LICENSE
└── README.md
