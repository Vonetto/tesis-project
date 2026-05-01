"""Helpers for Metro reconstruction output shaping."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Sequence


def sync_trip_level_terminals_from_legs(
    out: MutableMapping[str, Any],
    legs_out: Sequence[Mapping[str, Any]],
) -> MutableMapping[str, Any]:
    """
    Align trip-level origin/destination fields with reconstructed legs.
    """
    if not legs_out:
        return out

    first_leg = legs_out[0]
    out["paradero_inicio_viaje"] = first_leg.get("paradero_subida")
    out["zona_inicio_viaje"] = first_leg.get("zona_subida")

    last_stop = next(
        (leg.get("paradero_bajada") for leg in reversed(legs_out) if leg.get("paradero_bajada") is not None),
        None,
    )
    last_zone = next(
        (leg.get("zona_bajada") for leg in reversed(legs_out) if leg.get("zona_bajada") is not None),
        None,
    )
    out["paradero_fin_viaje"] = last_stop
    out["zona_fin_viaje"] = last_zone
    return out
