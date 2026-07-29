from argparse import Namespace

import numpy as np
import polars as pl

from scripts.audits.run_user_ml_benchmark import (
    local_qr_exposure_fold_features,
    prepare_local_qr_exposure_data,
)


def test_local_qr_exposure_uses_train_fold_and_leave_one_out():
    df = pl.DataFrame({"zona_hogar": ["A", "A", "B", "B", "A"]})
    y_binary = np.array([1, 0, 0, 1, 1])
    args = Namespace(
        local_qr_exposure=True,
        local_qr_exposure_min_count=1,
        local_qr_exposure_smoothing=0.0,
    )
    exposure = prepare_local_qr_exposure_data(df, y_binary, args)

    train_features, test_features = local_qr_exposure_fold_features(
        exposure,
        stats_idx=np.array([0, 1, 2, 3]),
        train_idx=np.array([0, 1]),
        test_idx=np.array([4]),
        args=args,
    )

    assert exposure.feature_names == ["lqe_home_zone_qr_rate"]
    np.testing.assert_allclose(train_features[:, 0], [0.0, 1.0])
    np.testing.assert_allclose(test_features[:, 0], [0.5])


def test_local_qr_exposure_falls_back_to_train_global_rate_for_small_groups():
    df = pl.DataFrame({"zona_hogar": ["A", "A", "B", "B", "C"]})
    y_binary = np.array([1, 0, 0, 1, 1])
    args = Namespace(
        local_qr_exposure=True,
        local_qr_exposure_min_count=3,
        local_qr_exposure_smoothing=0.0,
    )
    exposure = prepare_local_qr_exposure_data(df, y_binary, args)

    train_features, test_features = local_qr_exposure_fold_features(
        exposure,
        stats_idx=np.array([0, 1, 2, 3]),
        train_idx=np.array([0, 1]),
        test_idx=np.array([4]),
        args=args,
    )

    np.testing.assert_allclose(train_features[:, 0], [0.5, 0.5])
    np.testing.assert_allclose(test_features[:, 0], [0.5])
