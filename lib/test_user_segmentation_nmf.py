import numpy as np
import polars as pl

from scripts.audits.build_user_mobility_segmentation_matrix import (
    TARGET_METADATA_COLS,
    assert_no_target_leakage,
    feature_name_from_pattern,
    min_across_columns,
    mode_coarse_expr,
    normalize_feature_block,
    sanitize_token_expr,
    time_band_expr,
    write_audits,
)
from scripts.audits.run_user_nmf_segmentation import fit_one_nmf, parse_k_range
from scripts.audits.summarize_user_nmf_segments import cramers_v, summarize_for_k


def test_segmentation_mode_coarse_uses_numeric_transport_codes() -> None:
    mode_cols = [f"tipo_transporte_{i}" for i in range(1, 7)]
    df = pl.DataFrame(
        {
            mode_cols[0]: ["1", "2", "1", None, "3", "4"],
            mode_cols[1]: [None, None, "2", None, None, None],
            mode_cols[2]: [None, None, None, None, None, None],
            mode_cols[3]: [None, None, None, None, None, None],
            mode_cols[4]: [None, None, None, None, None, None],
            mode_cols[5]: [None, None, None, None, None, None],
        }
    )
    out = df.with_columns(mode_coarse_expr("mode"))
    assert out["mode"].to_list() == [
        "bus_only",
        "metro_only",
        "metro_bus",
        "other_mode",
        "bus_only",
        "metro_only",
    ]


def test_time_band_expr_maps_v2_dummies() -> None:
    df = pl.DataFrame(
        {
            "DUMMY_LAB_PM": [1, 0, 0, 0, 0],
            "DUMMY_LAB_PT": [0, 1, 0, 0, 0],
            "DUMMY_LAB_VALLE": [0, 0, 1, 0, 0],
            "DUMMY_NO_LAB": [0, 0, 0, 1, 0],
        }
    )
    out = df.with_columns(time_band_expr("band"))
    assert out["band"].to_list() == [
        "lab_am_peak",
        "lab_pm_peak",
        "lab_valle",
        "no_lab",
        "unknown_time",
    ]


def test_normalize_feature_block_share_rows_sum_to_one() -> None:
    df = pl.DataFrame({"id_tarjeta": ["a", "b"], "seg_a": [2.0, 0.0], "seg_b": [6.0, 0.0]})
    out = normalize_feature_block(df, ["seg_a", "seg_b"], "share")
    assert out["seg_a"].to_list() == [0.25, 0.0]
    assert out["seg_b"].to_list() == [0.75, 0.0]


def test_min_across_columns_handles_multiple_feature_columns() -> None:
    df = pl.DataFrame({"seg_a": [2.0, 3.0], "seg_b": [0.5, 1.0]})
    assert min_across_columns(df, ["seg_a", "seg_b"]) == 0.5


def test_feature_inventory_rejects_target_leakage_tokens() -> None:
    assert_no_target_leakage(["seg_norte__lab_am_peak__bus_only"])
    try:
        assert_no_target_leakage(["seg_qr__lab_am_peak__bus_only"])
    except ValueError as exc:
        assert "leaks" in str(exc)
    else:
        raise AssertionError("Expected target leakage guard to fail")


def test_target_metadata_cols_are_not_feature_cols_by_contract() -> None:
    assert set(TARGET_METADATA_COLS) == {"tipo_tarjeta", "is_qr", "is_qr_red", "is_qr_other"}


def test_sanitize_token_expr_builds_stable_ascii_tokens() -> None:
    df = pl.DataFrame({"raw": ["EXTERNA ESPECIAL", "lab-am peak", None]})
    out = df.with_columns(sanitize_token_expr(pl.col("raw")).alias("token"))
    assert out["token"].to_list() == ["externa_especial", "lab_am_peak", "unknown"]


def test_feature_name_from_pattern_uses_single_prefix_separator() -> None:
    assert (
        feature_name_from_pattern("ORIENTE", "lab_am_peak", "metro_only")
        == "seg_oriente__lab_am_peak__metro_only"
    )


def test_write_audits_handles_multiple_features(tmp_path) -> None:
    df = pl.DataFrame(
        {
            "id_tarjeta": ["a", "b"],
            "is_qr": [1, 0],
            "seg_a": [0.5, 0.0],
            "seg_b": [0.5, 1.0],
        }
    )
    out_path = tmp_path / "matrix.parquet"
    write_audits(df, ["seg_a", "seg_b"], out_path, normalization="share", matrix_spec="toy")
    summary_path = tmp_path / "matrix_summary.csv"
    assert summary_path.exists()
    summary = pl.read_csv(summary_path)
    assert "sparsity" in summary["metric"].to_list()


def test_parse_k_range_supports_range_and_list() -> None:
    assert parse_k_range("2-4") == [2, 3, 4]
    assert parse_k_range("4,2,3") == [2, 3, 4]


def test_fit_one_nmf_returns_nonnegative_shapes() -> None:
    x = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.9, 0.1, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.9, 0.1],
        ],
        dtype=np.float32,
    )
    result = fit_one_nmf(x, k=2, seed=7, max_iter=200, tol=1e-4, blas_threads=1)
    assert result.w_sample.shape == (4, 2)
    assert result.h.shape == (2, 3)
    assert np.all(result.w_sample >= 0)
    assert np.all(result.h >= 0)
    assert result.labels_sample.shape == (4,)


def test_cramers_v_for_perfect_binary_association_is_positive() -> None:
    chi2, v = cramers_v(np.array([[10, 0], [0, 10]]))
    assert chi2 > 0
    assert v > 0.9


def test_summarize_for_k_uses_generic_segment_column() -> None:
    joined = pl.DataFrame(
        {
            "segment_k4": [0, 0, 1, 1],
            "is_qr": [1, 0, 0, 0],
            "is_qr_red": [0, 0, 0, 0],
            "is_qr_other": [1, 0, 0, 0],
            "tipo_tarjeta": ["QR_OTHER", "BIP", "BIP", "BIP"],
            "n_viajes": [10, 12, 5, 7],
            "share_trips_2025": [0.5, 0.4, 0.7, 0.6],
        }
    )
    summary, association, _ = summarize_for_k(joined, 4)
    assert "segment" in summary.columns
    assert "segment_k4" not in summary.columns
    assert association["k"].to_list() == [4, 4]
