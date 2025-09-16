import pandas as pd


def test_report_outputs_have_deterministic_filenames(tmp_path):
    from metrics.reports import write_csv_report, write_png_lineplot, write_html_summary

    df = pd.DataFrame({"y": [1, 2, 3]})
    series = df["y"]

    out_dir = tmp_path
    stem = "demo"
    run_id = "20250101"

    csv_path = write_csv_report(df, out_dir=out_dir, stem=stem, run_id=run_id)
    png_path = write_png_lineplot(series, out_dir=out_dir, stem=stem, run_id=run_id)
    html_path = write_html_summary(
        {"rmse": 1.23, "mae": 0.45}, out_dir=out_dir, stem=stem, run_id=run_id
    )

    assert csv_path.name == f"{stem}_{run_id}.csv"
    assert png_path.name == f"{stem}_{run_id}.png"
    assert html_path.name == f"{stem}_{run_id}.html"

    assert csv_path.exists()
    assert png_path.exists()
    assert html_path.exists()
