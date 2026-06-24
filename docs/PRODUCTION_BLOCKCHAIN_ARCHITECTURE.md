# AGILANG/SBQ Production Blockchain Architecture

This document defines the required architecture direction for generated AGILANG blockchain projects. The generated blockchain app must not be local-only. It must provide both:

1. **Local/devnet profile** for workstation testing, CI, private labs, and MetaMask testing on loopback RPC.
2. **Production/staging profile** for private-chain or controlled production environments with TLS termination, RPC rate limits, storage durability, validator separation, and audit evidence gates.

## Runtime profiles

Generated projects should include:

- `.env.example` for local development.
- `.env.production.example` for production/staging configuration.
- `config/profiles/local.json` for developer and CI use.
- `config/profiles/production.json` for production/staging baseline.
- `config/validators.internal.json` for local/staging internal validator mode.
- `config/validators.external.example.json` for external validator/beacon-node topology.
- `config/metamask.json` for local and production wallet network settings.
- `config/contracts.example.json` for smart-contract deployment receipts.

## Node roles

### Internal validator node

Internal validator mode is for local, CI, private labs, and controlled staging. It may run block production and local signing in the same environment, but it must not be treated as the final public real-value topology.

### External validator/beacon node

Production validator architecture should separate public RPC, beacon participation, validator identity, and signing controls. External validators should be registered with endpoint metadata, stake allocation, fee-recipient information, and audited key-management references.

### RPC node

RPC nodes expose JSON-RPC for MetaMask, explorers, wallets, and backend services. Production RPC should run behind TLS, CORS restrictions, request-size limits, rate limits, monitoring, and log aggregation.

### Archive/storage node

Storage nodes preserve chain history and support recovery. Production storage must have backups, integrity checks, restart tests, and recovery drills.

## MetaMask and smart-contract workflow

The generated project should support MetaMask through a local profile and a production profile. Smart-contract deployments should not be accepted only because a transaction hash exists. Acceptance should require:

- receipt exists;
- receipt status is successful;
- block is finalized by configured finality depth;
- deployed bytecode or ABI hash matches the expected artifact;
- deployment record is stored in the receipt registry.

## Readiness boundary

The production readiness gate may pass engineering simulations but must still remain blocked for real-value launch until evidence exists for:

- independent external security audit;
- validator key-management audit;
- independent consensus/finality review.

This keeps the system useful for local, staging, and private-chain deployments while preserving an honest boundary for public real-value operation.
