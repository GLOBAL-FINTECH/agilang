import json
from pathlib import Path

from agilang.blockchain_runtime_gateway import generate_blockchain_app


def test_blockchain_generator_emits_local_and_production_profiles(tmp_path: Path) -> None:
    result = generate_blockchain_app('Production Profile Chain', tmp_path, force=True)
    root = Path(result['root'])

    expected = [
        root / '.env.example',
        root / '.env.production.example',
        root / 'config' / 'profiles' / 'local.json',
        root / 'config' / 'profiles' / 'production.json',
        root / 'config' / 'validators.internal.json',
        root / 'config' / 'validators.external.example.json',
        root / 'config' / 'metamask.json',
        root / 'config' / 'contracts.example.json',
        root / 'docs' / 'PRODUCTION_ARCHITECTURE.md',
        root / 'docs' / 'VALIDATOR_WORKFLOW.md',
        root / 'docs' / 'METAMASK_CONTRACTS_RECEIPTS.md',
        root / 'docs' / 'STORAGE_DURABILITY.md',
    ]
    for path in expected:
        assert path.exists(), path

    assert not (root / 'scripts' / 'start_rpc_server.py').exists()
    assert not (root / 'scripts' / 'chain_status.py').exists()

    production = json.loads((root / 'config' / 'profiles' / 'production.json').read_text())
    assert production['profile'] == 'production'
    assert production['validator']['mode'] == 'external'
    assert production['validator']['dev_signing_keys_allowed'] is False
    assert production['rpc']['tls_required_at_proxy'] is True
    assert production['storage']['backup_required'] is True

    metamask = json.loads((root / 'config' / 'metamask.json').read_text())
    assert metamask['local']['rpcUrl'].startswith('http://127.0.0.1')
    assert metamask['production']['rpcUrl'].startswith('https://')

    docs = (root / 'docs' / 'PRODUCTION_ARCHITECTURE.md').read_text()
    assert 'Local/devnet profile' in docs
    assert 'Production/staging profile' in docs
    assert 'External validator beacon node' in docs
