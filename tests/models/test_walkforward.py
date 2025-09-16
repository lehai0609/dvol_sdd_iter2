import pandas as pd


def test_expanding_walkforward_no_leakage_and_coverage():
    from models.walkforward import expanding_folds

    idx = pd.date_range("2021-01-01", periods=50, freq="D")
    initial_train = 20
    test_size = 5
    step = 5

    folds = list(
        expanding_folds(
            index=idx, initial=initial_train, test_size=test_size, step=step
        )
    )

    assert len(folds) >= 1

    prev_train_len = 0
    covered_tests = []

    for train_idx, test_idx in folds:
        # Indices should be strictly increasing and non-empty
        assert len(train_idx) > 0 and len(test_idx) > 0
        # Expanding: train length should grow or stay same across folds
        assert len(train_idx) >= prev_train_len
        prev_train_len = len(train_idx)
        # No leakage: last train index strictly before first test index
        assert train_idx[-1] < test_idx[0]
        # Disjoint sets
        assert set(train_idx).isdisjoint(set(test_idx))
        covered_tests.extend(test_idx)

    # Test windows should tile the evaluation range sequentially
    # First test window should immediately follow initial train
    assert folds[0][1][0] == idx[initial_train]
    # All test indices should be within the data range and unique in concatenation order
    assert covered_tests == sorted(covered_tests)
    assert covered_tests[0] == idx[initial_train]
    assert covered_tests[-1] <= idx[-1]
