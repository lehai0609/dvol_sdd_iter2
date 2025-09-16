def test_reproduce_run_one_slice_with_mocked_data():
    # Intentionally call the orchestrator; implementation will be provided later
    from models.reproduce import replay_one_slice

    asset = "BTC"
    start = "2021-01-01"
    end = "2021-02-01"

    # Expect a dict-like result with minimal keys when implemented
    result = replay_one_slice(asset=asset, start=start, end=end, config={"mock": True})

    assert isinstance(result, dict)
    assert "predictions" in result
    assert "metrics" in result
    assert "artifacts_dir" in result
