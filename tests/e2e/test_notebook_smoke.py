from nbformat import v4 as nbf
from nbclient import NotebookClient


def test_notebook_smoke_executes_with_mock_data(tmp_path):
    # Create a tiny notebook with a few cells
    nb = nbf.new_notebook()
    nb.cells = [
        nbf.new_markdown_cell("# DVOL Pipeline Smoke Test"),
        nbf.new_code_cell("import numpy as np, pandas as pd\nprint('ok-imports')"),
        nbf.new_code_cell(
            "df = pd.DataFrame({'a':[1,2,3]})\nassert df.shape == (3,1)\nprint('ok-data')"
        ),
        nbf.new_code_cell(
            "x = np.arange(5).sum()\nassert x == 10\nprint('ok-compute')"
        ),
    ]

    nb_path = tmp_path / "smoke.ipynb"
    import nbformat

    nbformat.write(nb, nb_path)

    client = NotebookClient(nb, timeout=60, kernel_name="python3")
    executed = client.execute()

    # Verify last cell executed and printed expected output
    outputs = executed.cells[-1].get("outputs", [])
    texts = (
        "\n".join(
            [o.get("text", "") for o in outputs if o.get("output_type") == "stream"]
        )
        if outputs
        else ""
    )
    assert "ok-compute" in texts
