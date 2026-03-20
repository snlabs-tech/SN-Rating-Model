from .run_from_excel import run_from_excel_with_bands


def _format_ratio_log(rows):
    header = (
        "Name                           Value    Score   Weight    "
        "PeerAvg  PeerFlg  Distress"
    )
    sep = "-" * len(header)
    lines = ["=== Ratio log (T0) ===", header, sep]
    for r in rows:
        name = str(r.get("Name", ""))
        val = r.get("Value", "")
        score = r.get("Score", "")
        weight = r.get("Weight", "")
        peer_avg = r.get("PeerAvg", "")
        peer_flag = r.get("PeerFlag", "")
        distress = r.get("DistressNotches", 0)

        lines.append(
            f"{name:<30} {val:>8.2f} {score:>7.2f} {weight:>8.2f} "
            f"{str(peer_avg):>9} {str(peer_flag):>7} {distress:>8}"
        )
    return "\n".join(lines)


def _format_qual_log(rows):
    header = "Name                                   Value    Score   Weight       Bucket"
    sep = "-" * len(header)
    lines = ["=== Qualitative factors (T0) ===", header, sep]
    for r in rows:
        name = str(r.get("Name", ""))
        val = r.get("Value", "")
        score = r.get("Score", "")
        weight = r.get("Weight", "")
        bucket = r.get("Bucket", "")
        lines.append(
            f"{name:<40} {val:>5} {score:>8.2f} {weight:>8.2f}{bucket:>12}"
        )
    return "\n".join(lines)


def main() -> None:
    res = run_from_excel_with_bands(horizon="t0")

    # Print tables to console
    print()
    print(_format_ratio_log(res.ratio_log))
    print()
    print(_format_qual_log(res.qual_log))
    print()
    print(f"Final rating: {res.final_rating}, outlook: {res.final_outlook}")
    print(
        f"Report generated successfully: "
        f"{__import__('pathlib').Path.cwd() / 'output' / (res.issuer_name.replace(' ', '_') + '_Corporate_Credit_Rating_Report.xlsx')}"
    )


if __name__ == "__main__":
    main()
