from argparse import Namespace

import scripts.audits.summarize_user_ml_hard_labels as summarize


def test_collect_run_ids_from_oof_predictions_when_config_is_missing(tmp_path, monkeypatch):
    run_id = (
        "undersample_binary_qr0.25_interannual_ml_clean_alta_n3_"
        "full_plus_rhythm_context_routine_daily_tour_binary_xgb_random_50297161"
    )
    (tmp_path / f"oof_predictions_{run_id}_binary.parquet").touch()
    monkeypatch.setattr(summarize, "OUT_DIR", tmp_path)

    args = Namespace(run_id=[], run_id_prefix=["undersample_binary_qr"])

    assert summarize.collect_run_ids(args) == [run_id]


def test_main_uses_benchmark_dir_override(tmp_path, monkeypatch, capsys):
    run_id = (
        "undersample_binary_qr0.25_interannual_ml_clean_alta_n3_"
        "full_plus_rhythm_context_routine_daily_tour_binary_xgb_random_50297161"
    )
    (tmp_path / f"oof_predictions_{run_id}_binary.parquet").touch()

    monkeypatch.setattr(
        "sys.argv",
        [
            "summarize_user_ml_hard_labels.py",
            "--run-id-prefix",
            "undersample_binary_qr",
            "--benchmark-dir",
            str(tmp_path),
        ],
    )
    monkeypatch.setattr(summarize, "binary_summary", lambda *_args: {"run_id": run_id, "metric_scope": "binary"})
    monkeypatch.setattr(summarize, "multiclass_summary", lambda *_args: None)

    summarize.main()

    assert f"OK: {tmp_path / 'hard_label_summary_hard_label_summary.csv'}" in capsys.readouterr().out
