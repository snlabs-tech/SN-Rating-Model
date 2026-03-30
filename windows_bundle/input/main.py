import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sn_rating_v3.run_from_excel import run_v3_from_excel_with_bands
from sn_rating_v3.report import generate_corporate_rating_report_v3


def set_working_dir():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = BASE_DIR
    os.chdir(base)


if __name__ == "__main__":
    set_working_dir()

    out_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(out_dir, exist_ok=True)

    res = run_v3_from_excel_with_bands()

    final_path = generate_corporate_rating_report_v3(res)

    print("Report written to:", final_path)



