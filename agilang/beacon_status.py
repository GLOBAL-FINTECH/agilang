"""Status helpers for AGILANG native SBQ Beacon consensus."""
from pathlib import Path
from typing import Any, Dict

from .beacon import BeaconStore, beacon_capabilities


def beacon_status(path: str | Path = "storage/beacon.sqlite") -> Dict[str, Any]:
    store = BeaconStore(path)
    state = store.load_state()
    return {"ok": True, "capabilities": beacon_capabilities(), "state": state.as_dict()}


__all__ = ["beacon_status"]
