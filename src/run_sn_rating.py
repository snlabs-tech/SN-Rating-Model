# run_sn_rating.py at project root

from sn_rating.run_from_excel import run_from_excel_with_bands   # High-level model runner
from sn_rating.report import generate_corporate_rating_report    # Build Excel report


def print_ratio_log_cli(res):
    """Pretty-print quantitative ratio log for T0 to the console."""
    
    print("\n=== Ratio log (T0) ===")
    header = (
        f"{'Name':25} {'Value':>10} {'Score':>8} {'Weight':>8} "
        f"{'PeerAvg':>10} {'PeerFlg':>8} {'Distress':>9}"
    )
    print(header)
    print("-" * len(header))

    for row in res.ratio_log:
        name = row.get("Name")
        if not name or name == "peer_positioning":         # Skip blank + aggregate row
            continue

        value = row.get("Value")
        score = row.get("Score")
        weight = row.get("Weight")
        peer_avg = row.get("PeerAvg")
        peer_flag = row.get("PeerFlag") or ""
        distress = row.get("DistressNotches", 0)

        print(
            f"{name:25}"                                   # Left-align name in 25 chars
            f"{(f'{value:.2f}' if isinstance(value, (int, float)) else (str(value) if value is not None else '')):>10}"
            f"{(f'{score:.2f}' if isinstance(score, (int, float)) else ''):>8}"
            f"{(f'{weight:.2f}' if isinstance(weight, (int, float)) else ''):>8}"
            f"{(f'{peer_avg:.2f}' if isinstance(peer_avg, (int, float)) else ''):>10}"
            f"{peer_flag:>8}"
            f"{int(distress) if isinstance(distress, (int, float)) else 0:>9}"
        )


def print_qual_log_cli(res):
    """Pretty-print qualitative factor log for T0 to the console, if present."""
    
    if not getattr(res, "qual_log", None):                 # If model didn't populate qual_log
        return

    print("\n=== Qualitative factors (T0) ===")
    header = f"{'Name':35} {'Value':>8} {'Score':>8} {'Weight':>8} {'Bucket':>12}"
    print(header)
    print("-" * len(header))

    for row in res.qual_log:
        name = row.get("Name")
        value = row.get("Value")
        score = row.get("Score")
        weight = row.get("Weight")
        bucket = row.get("Bucket")

        print(
            f"{name:35}"                                   # Left-align name in 35 chars
            f"{(str(value) if value is not None else ''):>8}"
            f"{(f'{score:.2f}' if isinstance(score, (int, float)) else ''):>8}"
            f"{(f'{weight:.2f}' if isinstance(weight, (int, float)) else ''):>8}"
            f"{(str(bucket) if bucket is not None else ''):>12}"
        )


def main():
    """Run model from Excel, generate report, and print CLI logs."""
    
    res = run_from_excel_with_bands()                     # 1) Read Excel → run RatingModel
    out_file = generate_corporate_rating_report(res)      # 2) Build Excel report workbook
    print_ratio_log_cli(res)                              # 3) Dump quantitative log to stdout
    print_qual_log_cli(res)                               # 4) Dump qualitative log to stdout
    print(f"\nReport generated successfully: {out_file}") # 5) Show output path


if __name__ == "__main__":                                # Script entry point
    main()
