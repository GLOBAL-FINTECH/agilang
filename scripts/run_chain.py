"""Unified production in-house Smart Chain starter.

Starts the configured execution node, RPC endpoint, built-in validator producer,
and SBQ beacon loop from config/chain-services.json.
"""
from __future__ import annotations

from agilang.inhouse_chain import main


if __name__ == "__main__":
    raise SystemExit(main())
