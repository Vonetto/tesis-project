import polars as pl

from scripts.audits.build_user_daily_tour_features import (
    MODE_COLS as DAILY_MODE_COLS,
    mode_coarse_expr as daily_mode_coarse_expr,
)
from scripts.audits.build_user_routine_features import (
    MODE_COLS as ROUTINE_MODE_COLS,
    mode_coarse_expr as routine_mode_coarse_expr,
)


def _mode_code_frame(mode_cols: list[str]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            mode_cols[0]: ["1", "2", "1", None, "3", "4"],
            mode_cols[1]: [None, None, "2", None, None, None],
            mode_cols[2]: [None, None, None, None, None, None],
            mode_cols[3]: [None, None, None, None, None, None],
            mode_cols[4]: [None, None, None, None, None, None],
            mode_cols[5]: [None, None, None, None, None, None],
        }
    )


def test_daily_tour_mode_coarse_uses_numeric_transport_codes() -> None:
    out = _mode_code_frame(DAILY_MODE_COLS).with_columns(daily_mode_coarse_expr("mode"))
    assert out["mode"].to_list() == [
        "bus_only",
        "metro_only",
        "metro_bus",
        "other_mode",
        "bus_only",
        "metro_only",
    ]


def test_routine_mode_coarse_uses_numeric_transport_codes() -> None:
    out = _mode_code_frame(ROUTINE_MODE_COLS).with_columns(routine_mode_coarse_expr("mode"))
    assert out["mode"].to_list() == [
        "bus_only",
        "metro_only",
        "metro_bus",
        "other_mode",
        "bus_only",
        "metro_only",
    ]
