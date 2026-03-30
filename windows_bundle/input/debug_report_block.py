from sn_rating_v3.run_from_excel import run_v3_from_excel_with_bands
from sn_rating_v3.report import generate_corporate_rating_report_v3

if __name__ == "__main__":
    # 1) run the full model once to get `result`
    #    (adapt the args here to how you normally call it)
    result = run_v3_from_excel_with_bands(
        "v3_rating_input.xlsx",  # or path you actually use
        # other args if required...
    )

    # 2) call only the reporting function
    out_file = generate_corporate_rating_report_v3(result)
    print("Report saved to:", out_file)
