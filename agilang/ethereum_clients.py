"""Ethereum external-client orchestration for AGILANG.

AGILANG's native blockchain runtime is for SBQ/custom chains.  Ethereum
mainnet participation is intentionally delegated to the real Ethereum client
stack: an execution client, a consensus/beacon client and, for staking duties,
a validator client.  This module provides deterministic configuration,
planning, validation and optional process supervision for those clients without
pretending that AGILANG custom consensus can replace Ethereum consensus.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import request as urlrequest

_SUPPORTED_EXECUTION = {"geth", "nethermind", "besu", "erigon"}
_SUPPORTED_CONSENSUS = {"lighthouse", "prysm", "teku", "nimbus", "lodestar"}
_SUPPORTED_VALIDATOR = {"lighthouse", "prysm", "teku", "nimbus", "lodestar"}
_PRIVATE_HOSTS = {"127.0.0.1", "localhost", "::1"}
_PUBLIC_HOSTS = {"0.0.0.0", "::", "", "*"}


@dataclass
class EthereumEndpoint:
    name: str
    host: str
    port: int
    public: bool = False
    purpose: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "host": self.host,
            "port": int(self.port),
            "public": bool(self.public),
            "url": f"http://{self.host}:{int(self.port)}",
            "purpose": self.purpose,
        }


@dataclass
class EthereumClientStackConfig:
    network: str = "mainnet"
    mode: str = "full"  # full, archive, validator, all
    data_dir: str = "ethereum-data"
    jwt_secret_path: str = "ethereum-data/jwt.hex"
    execution_client: str = "geth"
    consensus_client: str = "lighthouse"
    validator_client: str = "lighthouse"
    validator_enabled: bool = False
    archive: bool = False
    checkpoint_sync_url: str = ""
    fee_recipient: str = ""
    graffiti: str = "AGILANG"
    execution_rpc: EthereumEndpoint = field(default_factory=lambda: EthereumEndpoint("execution_rpc", "127.0.0.1", 8545, False, "Ethereum execution JSON-RPC"))
    execution_authrpc: EthereumEndpoint = field(default_factory=lambda: EthereumEndpoint("execution_authrpc", "127.0.0.1", 8551, False, "Engine API authenticated RPC"))
    execution_ws: EthereumEndpoint = field(default_factory=lambda: EthereumEndpoint("execution_ws", "127.0.0.1", 8546, False, "Execution WebSocket RPC"))
    consensus_http: EthereumEndpoint = field(default_factory=lambda: EthereumEndpoint("consensus_http", "127.0.0.1", 5052, False, "Beacon REST API"))
    validator_http: EthereumEndpoint = field(default_factory=lambda: EthereumEndpoint("validator_http", "127.0.0.1", 5062, False, "Private validator API"))
    metrics: EthereumEndpoint = field(default_factory=lambda: EthereumEndpoint("metrics", "127.0.0.1", 9101, False, "Ethereum client metrics"))

    def endpoints(self) -> List[EthereumEndpoint]:
        endpoints = [self.execution_rpc, self.execution_authrpc, self.execution_ws, self.consensus_http, self.metrics]
        if self.validator_enabled or self.mode in {"validator", "all"}:
            endpoints.append(self.validator_http)
        return endpoints

    def as_dict(self) -> Dict[str, Any]:
        return {
            "network": self.network,
            "mode": self.mode,
            "data_dir": self.data_dir,
            "jwt_secret_path": self.jwt_secret_path,
            "execution_client": self.execution_client,
            "consensus_client": self.consensus_client,
            "validator_client": self.validator_client,
            "validator_enabled": bool(self.validator_enabled),
            "archive": bool(self.archive),
            "checkpoint_sync_url": self.checkpoint_sync_url,
            "fee_recipient": self.fee_recipient,
            "graffiti": self.graffiti,
            "endpoints": {endpoint.name: endpoint.as_dict() for endpoint in self.endpoints()},
            "consensus_boundary": {
                "ethereum_consensus_provider": "external_consensus_client",
                "agilang_custom_consensus_on_ethereum_mainnet": False,
                "reason": "Ethereum mainnet validation requires Ethereum consensus and validator clients; AGILANG custom consensus remains for SBQ/custom chains.",
            },
        }


def ethereum_client_capabilities() -> Dict[str, Any]:
    return {
        "ethereum_external_clients": [
            "execution_client_orchestration",
            "consensus_beacon_client_orchestration",
            "validator_client_orchestration",
            "engine_api_jwt_secret_management",
            "archive_execution_profile",
            "checkpoint_sync_configuration",
            "private_validator_api_port",
            "one_command_ethereum_full_archive_validator_profiles",
            "installed_client_detection",
            "dry_run_safe_command_plans",
        ],
        "supported_execution_clients": sorted(_SUPPORTED_EXECUTION),
        "supported_consensus_clients": sorted(_SUPPORTED_CONSENSUS),
        "supported_validator_clients": sorted(_SUPPORTED_VALIDATOR),
        "ethereum_truth_boundary": {
            "native_agilang_custom_consensus_can_validate_ethereum_mainnet": False,
            "ethereum_validation_requires_external_consensus_and_validator_clients": True,
            "agilang_role": "orchestrator_supervisor_rpc_bridge_and_custom_chain_runtime",
        },
    }


def _endpoint_from_dict(name: str, data: Dict[str, Any], default: EthereumEndpoint) -> EthereumEndpoint:
    return EthereumEndpoint(
        name=name,
        host=str(data.get("host", default.host)),
        port=int(data.get("port", default.port)),
        public=bool(data.get("public", default.public)),
        purpose=str(data.get("purpose", default.purpose)),
    )


def default_ethereum_client_config(**overrides: Any) -> EthereumClientStackConfig:
    cfg = EthereumClientStackConfig()
    for key, value in overrides.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)
    if cfg.mode in {"archive", "all"}:
        cfg.archive = True
    if cfg.mode in {"validator", "all"}:
        cfg.validator_enabled = True
    return cfg


def load_ethereum_client_config(path: str | Path = "config/ethereum-clients.json") -> EthereumClientStackConfig:
    p = Path(path)
    if not p.exists():
        return default_ethereum_client_config()
    data = json.loads(p.read_text(encoding="utf-8"))
    defaults = default_ethereum_client_config()
    endpoints = data.get("endpoints", {}) if isinstance(data.get("endpoints", {}), dict) else {}
    cfg = EthereumClientStackConfig(
        network=str(data.get("network", defaults.network)),
        mode=str(data.get("mode", defaults.mode)),
        data_dir=str(data.get("data_dir", defaults.data_dir)),
        jwt_secret_path=str(data.get("jwt_secret_path", defaults.jwt_secret_path)),
        execution_client=str(data.get("execution_client", defaults.execution_client)).lower(),
        consensus_client=str(data.get("consensus_client", defaults.consensus_client)).lower(),
        validator_client=str(data.get("validator_client", defaults.validator_client)).lower(),
        validator_enabled=bool(data.get("validator_enabled", defaults.validator_enabled)),
        archive=bool(data.get("archive", defaults.archive)),
        checkpoint_sync_url=str(data.get("checkpoint_sync_url", defaults.checkpoint_sync_url)),
        fee_recipient=str(data.get("fee_recipient", defaults.fee_recipient)),
        graffiti=str(data.get("graffiti", defaults.graffiti)),
        execution_rpc=_endpoint_from_dict("execution_rpc", endpoints.get("execution_rpc", {}), defaults.execution_rpc),
        execution_authrpc=_endpoint_from_dict("execution_authrpc", endpoints.get("execution_authrpc", {}), defaults.execution_authrpc),
        execution_ws=_endpoint_from_dict("execution_ws", endpoints.get("execution_ws", {}), defaults.execution_ws),
        consensus_http=_endpoint_from_dict("consensus_http", endpoints.get("consensus_http", {}), defaults.consensus_http),
        validator_http=_endpoint_from_dict("validator_http", endpoints.get("validator_http", {}), defaults.validator_http),
        metrics=_endpoint_from_dict("metrics", endpoints.get("metrics", {}), defaults.metrics),
    )
    if cfg.mode in {"archive", "all"}:
        cfg.archive = True
    if cfg.mode in {"validator", "all"}:
        cfg.validator_enabled = True
    return cfg


def write_ethereum_client_config(path: str | Path = "config/ethereum-clients.json", **overrides: Any) -> Dict[str, Any]:
    cfg = default_ethereum_client_config(**overrides)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg.as_dict(), indent=2), encoding="utf-8")
    return {"ok": True, "path": str(p), "config": cfg.as_dict()}


def ensure_jwt_secret(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    created = False
    if not p.exists():
        p.write_text(os.urandom(32).hex(), encoding="utf-8")
        try:
            p.chmod(0o600)
        except Exception:
            pass
        created = True
    value = p.read_text(encoding="utf-8").strip()
    ok = len(value) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in value)
    return {"ok": ok, "path": str(p), "created": created, "length": len(value)}


def detect_installed_ethereum_clients() -> Dict[str, Any]:
    names = {
        "geth": ["geth"],
        "nethermind": ["Nethermind.Runner", "nethermind"],
        "besu": ["besu"],
        "erigon": ["erigon"],
        "lighthouse": ["lighthouse"],
        "prysm": ["beacon-chain", "validator"],
        "teku": ["teku"],
        "nimbus": ["nimbus_beacon_node", "nimbus_validator_client"],
        "lodestar": ["lodestar"],
    }
    found: Dict[str, Any] = {}
    for name, binaries in names.items():
        matches = {binary: shutil.which(binary) for binary in binaries}
        found[name] = {"installed": any(matches.values()), "binaries": matches}
    return found


def _validate_supported(cfg: EthereumClientStackConfig) -> List[str]:
    errors: List[str] = []
    if cfg.execution_client not in _SUPPORTED_EXECUTION:
        errors.append(f"unsupported_execution_client_{cfg.execution_client}")
    if cfg.consensus_client not in _SUPPORTED_CONSENSUS:
        errors.append(f"unsupported_consensus_client_{cfg.consensus_client}")
    if cfg.validator_client not in _SUPPORTED_VALIDATOR:
        errors.append(f"unsupported_validator_client_{cfg.validator_client}")
    if cfg.mode not in {"full", "archive", "validator", "all"}:
        errors.append(f"unsupported_ethereum_mode_{cfg.mode}")
    return errors


def validate_ethereum_client_config(cfg: EthereumClientStackConfig | Dict[str, Any] | None = None) -> Dict[str, Any]:
    if cfg is None:
        cfg = default_ethereum_client_config()
    if isinstance(cfg, dict):
        tmp = default_ethereum_client_config()
        for key, value in cfg.items():
            if hasattr(tmp, key):
                setattr(tmp, key, value)
        cfg = tmp
    errors = _validate_supported(cfg)
    warnings: List[str] = []
    ports: Dict[int, List[str]] = {}
    for endpoint in cfg.endpoints():
        ports.setdefault(int(endpoint.port), []).append(endpoint.name)
        if endpoint.name in {"execution_authrpc", "consensus_http", "validator_http", "metrics"}:
            if endpoint.public or endpoint.host not in _PRIVATE_HOSTS:
                errors.append(f"{endpoint.name}_must_bind_private_loopback")
        if endpoint.name == "execution_rpc" and endpoint.host in _PUBLIC_HOSTS and endpoint.public:
            warnings.append("execution_rpc_public_exposure_requires_firewall_and_rate_limits")
    for port, names in ports.items():
        if len(names) > 1:
            errors.append(f"port_collision_{port}_{'_'.join(names)}")
    if cfg.validator_enabled and not cfg.fee_recipient:
        warnings.append("validator_fee_recipient_not_set")
    if cfg.mode == "archive" and not cfg.archive:
        errors.append("archive_mode_requires_archive_true")
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "ports": {str(k): v for k, v in sorted(ports.items())},
        "validator_private": not any("validator_http_must_bind_private_loopback" == err for err in errors),
        "config": cfg.as_dict(),
    }


def _network_flag(network: str, client: str) -> List[str]:
    if client in {"geth", "lighthouse"}:
        return [f"--{network}"] if network != "mainnet" else ["--mainnet"]
    if client == "teku":
        return [f"--network={network}"]
    if client == "besu":
        return [f"--network={network}"]
    if client == "erigon":
        return [f"--chain={network}"]
    if client == "nethermind":
        return [f"--config", network]
    return [f"--network", network]


def execution_command(cfg: EthereumClientStackConfig) -> List[str]:
    data_dir = str(Path(cfg.data_dir) / cfg.execution_client)
    jwt = cfg.jwt_secret_path
    rpc = cfg.execution_rpc
    auth = cfg.execution_authrpc
    ws = cfg.execution_ws
    if cfg.execution_client == "geth":
        cmd = [
            "geth", *_network_flag(cfg.network, "geth"),
            "--datadir", data_dir,
            "--authrpc.addr", auth.host, "--authrpc.port", str(auth.port), "--authrpc.jwtsecret", jwt,
            "--http", "--http.addr", rpc.host, "--http.port", str(rpc.port), "--http.api", "eth,net,web3,engine,debug",
            "--ws", "--ws.addr", ws.host, "--ws.port", str(ws.port), "--ws.api", "eth,net,web3",
            "--syncmode", "full" if cfg.archive else "snap",
        ]
        if cfg.archive:
            cmd.append("--gcmode=archive")
        return cmd
    if cfg.execution_client == "nethermind":
        return [
            "Nethermind.Runner", *_network_flag(cfg.network, "nethermind"),
            "--datadir", data_dir,
            "--JsonRpc.Enabled", "true", "--JsonRpc.Host", rpc.host, "--JsonRpc.Port", str(rpc.port),
            "--JsonRpc.EngineHost", auth.host, "--JsonRpc.EnginePort", str(auth.port), "--JsonRpc.JwtSecretFile", jwt,
            "--Sync.DownloadBodiesInFastSync", "true",
            "--Pruning.Mode", "None" if cfg.archive else "Hybrid",
        ]
    if cfg.execution_client == "besu":
        cmd = [
            "besu", *_network_flag(cfg.network, "besu"), "--data-path", data_dir,
            "--engine-rpc-enabled", "--engine-host-allowlist=*", "--engine-jwt-secret", jwt,
            "--rpc-http-enabled", "--rpc-http-host", rpc.host, "--rpc-http-port", str(rpc.port),
            "--rpc-ws-enabled", "--rpc-ws-host", ws.host, "--rpc-ws-port", str(ws.port),
        ]
        if cfg.archive:
            cmd.append("--data-storage-format=FOREST")
        return cmd
    if cfg.execution_client == "erigon":
        cmd = [
            "erigon", *_network_flag(cfg.network, "erigon"), "--datadir", data_dir,
            "--authrpc.addr", auth.host, "--authrpc.port", str(auth.port), "--authrpc.jwtsecret", jwt,
            "--http", "--http.addr", rpc.host, "--http.port", str(rpc.port), "--http.api", "eth,erigon,web3,net,debug,trace,txpool",
        ]
        if cfg.archive:
            cmd.append("--prune.mode=archive")
        return cmd
    raise ValueError(f"unsupported execution client: {cfg.execution_client}")


def consensus_command(cfg: EthereumClientStackConfig) -> List[str]:
    data_dir = str(Path(cfg.data_dir) / cfg.consensus_client)
    endpoint = f"http://{cfg.execution_authrpc.host}:{cfg.execution_authrpc.port}"
    beacon = cfg.consensus_http
    jwt = cfg.jwt_secret_path
    if cfg.consensus_client == "lighthouse":
        cmd = [
            "lighthouse", "beacon_node", *_network_flag(cfg.network, "lighthouse"),
            "--datadir", data_dir,
            "--execution-endpoint", endpoint,
            "--execution-jwt", jwt,
            "--http", "--http-address", beacon.host, "--http-port", str(beacon.port),
        ]
        if cfg.checkpoint_sync_url:
            cmd.extend(["--checkpoint-sync-url", cfg.checkpoint_sync_url])
        return cmd
    if cfg.consensus_client == "prysm":
        cmd = [
            "beacon-chain", f"--{cfg.network}", "--datadir", data_dir,
            f"--execution-endpoint={endpoint}", f"--jwt-secret={jwt}",
            f"--grpc-gateway-host={beacon.host}", f"--grpc-gateway-port={beacon.port}",
        ]
        if cfg.checkpoint_sync_url:
            cmd.append(f"--checkpoint-sync-url={cfg.checkpoint_sync_url}")
        return cmd
    if cfg.consensus_client == "teku":
        cmd = [
            "teku", *_network_flag(cfg.network, "teku"), "--data-path", data_dir,
            "--ee-endpoint", endpoint, "--ee-jwt-secret-file", jwt,
            "--rest-api-enabled=true", f"--rest-api-interface={beacon.host}", f"--rest-api-port={beacon.port}",
        ]
        if cfg.checkpoint_sync_url:
            cmd.append(f"--initial-state={cfg.checkpoint_sync_url}")
        return cmd
    if cfg.consensus_client == "nimbus":
        return [
            "nimbus_beacon_node", f"--network={cfg.network}", f"--data-dir={data_dir}",
            f"--web3-url={endpoint}", f"--jwt-secret={jwt}",
            "--rest", f"--rest-address={beacon.host}", f"--rest-port={beacon.port}",
        ]
    if cfg.consensus_client == "lodestar":
        cmd = [
            "lodestar", "beacon", f"--network={cfg.network}", f"--dataDir={data_dir}",
            f"--execution.urls={endpoint}", f"--jwt-secret={jwt}",
            "--rest", f"--rest.address={beacon.host}", f"--rest.port={beacon.port}",
        ]
        if cfg.checkpoint_sync_url:
            cmd.append(f"--checkpointSyncUrl={cfg.checkpoint_sync_url}")
        return cmd
    raise ValueError(f"unsupported consensus client: {cfg.consensus_client}")


def validator_command(cfg: EthereumClientStackConfig) -> List[str]:
    data_dir = str(Path(cfg.data_dir) / f"{cfg.validator_client}-validator")
    beacon = f"http://{cfg.consensus_http.host}:{cfg.consensus_http.port}"
    val = cfg.validator_http
    fee = cfg.fee_recipient or "0x0000000000000000000000000000000000000000"
    if cfg.validator_client == "lighthouse":
        return [
            "lighthouse", "validator_client", *_network_flag(cfg.network, "lighthouse"),
            "--datadir", data_dir,
            "--beacon-nodes", beacon,
            "--http", "--http-address", val.host, "--http-port", str(val.port),
            "--suggested-fee-recipient", fee,
            "--graffiti", cfg.graffiti,
        ]
    if cfg.validator_client == "prysm":
        return [
            "validator", f"--{cfg.network}", "--datadir", data_dir,
            f"--beacon-rpc-provider={cfg.consensus_http.host}:4000",
            f"--wallet-dir={Path(cfg.data_dir) / 'prysm-wallet'}",
            f"--suggested-fee-recipient={fee}",
            f"--graffiti={cfg.graffiti}",
        ]
    if cfg.validator_client == "teku":
        return [
            "teku", "validator-client", *_network_flag(cfg.network, "teku"),
            "--data-path", data_dir,
            f"--beacon-node-api-endpoint={beacon}",
            f"--validators-proposer-default-fee-recipient={fee}",
            f"--validators-graffiti={cfg.graffiti}",
        ]
    if cfg.validator_client == "nimbus":
        return [
            "nimbus_validator_client", f"--network={cfg.network}", f"--data-dir={data_dir}",
            f"--beacon-node={beacon}", f"--suggested-fee-recipient={fee}",
        ]
    if cfg.validator_client == "lodestar":
        return [
            "lodestar", "validator", f"--network={cfg.network}", f"--dataDir={data_dir}",
            f"--beaconNodes={beacon}", f"--suggestedFeeRecipient={fee}",
            f"--graffiti={cfg.graffiti}",
        ]
    raise ValueError(f"unsupported validator client: {cfg.validator_client}")


def ethereum_stack_plan(config: EthereumClientStackConfig | None = None, *, mode: Optional[str] = None) -> Dict[str, Any]:
    cfg = config or default_ethereum_client_config()
    if mode:
        cfg.mode = mode
    if cfg.mode in {"archive", "all"}:
        cfg.archive = True
    if cfg.mode in {"validator", "all"}:
        cfg.validator_enabled = True
    validation = validate_ethereum_client_config(cfg)
    commands: Dict[str, List[str]] = {}
    if validation["ok"]:
        commands["execution"] = execution_command(cfg)
        commands["consensus"] = consensus_command(cfg)
        if cfg.validator_enabled:
            commands["validator"] = validator_command(cfg)
    return {
        "ok": bool(validation["ok"]),
        "mode": cfg.mode,
        "network": cfg.network,
        "archive": bool(cfg.archive),
        "validator_enabled": bool(cfg.validator_enabled),
        "validation": validation,
        "commands": commands,
        "startup_order": list(commands.keys()),
        "boundary": "AGILANG starts/supervises real Ethereum EL/CL/validator clients; it does not replace Ethereum consensus with SBQ/AGILANG custom consensus.",
    }


def ethereum_stack_check(config_path: str | Path = "config/ethereum-clients.json", *, require_installed: bool = False) -> Dict[str, Any]:
    cfg = load_ethereum_client_config(config_path) if Path(config_path).exists() else default_ethereum_client_config()
    plan = ethereum_stack_plan(cfg)
    installed = detect_installed_ethereum_clients()
    selected = [cfg.execution_client, cfg.consensus_client]
    if cfg.validator_enabled:
        selected.append(cfg.validator_client)
    installed_ok = all(installed.get(client, {}).get("installed") for client in selected)
    checks = {
        "config_valid": bool(plan.get("ok")),
        "execution_client_planned": "execution" in plan.get("commands", {}),
        "consensus_client_planned": "consensus" in plan.get("commands", {}),
        "validator_client_planned_when_enabled": (not cfg.validator_enabled) or ("validator" in plan.get("commands", {})),
        "engine_api_private": cfg.execution_authrpc.host in _PRIVATE_HOSTS and not cfg.execution_authrpc.public,
        "validator_api_private": (not cfg.validator_enabled) or (cfg.validator_http.host in _PRIVATE_HOSTS and not cfg.validator_http.public),
        "archive_profile_consistent": (not cfg.archive) or (cfg.mode in {"archive", "all"} or cfg.archive),
        "selected_clients_installed": installed_ok if require_installed else True,
    }
    return {"ok": all(checks.values()), "checks": checks, "plan": plan, "installed": installed, "require_installed": require_installed}


def _json_rpc_post(url: str, method: str, params: Optional[List[Any]] = None, request_id: int = 1, timeout: int = 5) -> Dict[str, Any]:
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params or [], "id": request_id}).encode("utf-8")
    req = urlrequest.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urlrequest.urlopen(req, timeout=timeout) as response:  # noqa: S310 - user-configured local/upstream endpoint
        return json.loads(response.read().decode("utf-8"))


def ethereum_connectivity_smoke(execution_rpc_url: str = "", beacon_api_url: str = "") -> Dict[str, Any]:
    result: Dict[str, Any] = {"ok": True, "execution_rpc_configured": bool(execution_rpc_url), "beacon_api_configured": bool(beacon_api_url)}
    if execution_rpc_url:
        try:
            result["execution_chain_id"] = _json_rpc_post(execution_rpc_url, "eth_chainId")
        except Exception as exc:
            result["ok"] = False
            result["execution_error"] = str(exc)
    if beacon_api_url:
        try:
            with urlrequest.urlopen(beacon_api_url.rstrip("/") + "/eth/v1/node/health", timeout=5) as response:  # noqa: S310
                result["beacon_health_status"] = int(response.status)
        except Exception as exc:
            result["ok"] = False
            result["beacon_error"] = str(exc)
    return result


def start_ethereum_stack(config_path: str | Path = "config/ethereum-clients.json", *, mode: str = "full", dry_run: bool = False) -> Dict[str, Any]:
    cfg = load_ethereum_client_config(config_path)
    if mode:
        cfg.mode = mode
    plan = ethereum_stack_plan(cfg)
    if dry_run or not plan.get("ok"):
        return plan
    ensure_jwt_secret(cfg.jwt_secret_path)
    Path(cfg.data_dir).mkdir(parents=True, exist_ok=True)
    processes = []
    for name in plan.get("startup_order", []):
        cmd = plan["commands"][name]
        proc = subprocess.Popen(cmd)  # noqa: S603 - explicit user-selected Ethereum clients
        processes.append({"name": name, "pid": proc.pid, "command": cmd})
        time.sleep(2)
    return {"ok": True, "started": processes, "plan": plan}
