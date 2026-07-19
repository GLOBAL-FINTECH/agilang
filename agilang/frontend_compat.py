"""Smart Chain frontend compatibility manifest and generated dashboard assets."""
from __future__ import annotations

import json
from pathlib import Path


FRONTEND_API_CONTRACT = {
    "status": "/api/status",
    "status_details": "/api/status/details",
    "operations_live": "/api/operations/live",
    "operations_history": "/api/operations/history?range=1h",
    "contracts": "/api/contracts",
    "contract_builder": "/contracts/builder",
    "transactions": "/transactions",
    "blocks": "/blocks",
    "validators": "/validators",
    "beacon": "/beacon",
    "peers": "/peers",
    "resources": "/resources",
}


def write_frontend(root: Path, files: list[Path], *, title: str, chain_id: int) -> None:
    """Write a same-origin dashboard compatible with the complete Smart Chain API."""
    frontend = root / "frontend"
    assets = frontend / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    manifest = frontend / "api-contract.json"
    manifest.write_text(json.dumps(FRONTEND_API_CONTRACT, indent=2) + "\n", encoding="utf-8")
    files.append(manifest)

    html = frontend / "index.html"
    html.write_text(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} Observability</title><link rel="stylesheet" href="/frontend/assets/dashboard.css"></head>
<body><div class="layout"><aside><h2>AGILANG</h2><a href="/dashboard">Overview</a><a href="/transactions">Transactions</a><a href="/blocks">Blocks</a><a href="/validators">Validators</a><a href="/beacon">Beacon</a><a href="/peers">P2P</a><a href="/resources">Resources</a><a href="/contracts/builder">Contract Builder</a></aside><main>
<header><div><small>SMART CHAIN</small><h1>{title}</h1></div><span id="health">Connecting…</span></header>
<section class="kpis"><article><label>Chain ID</label><strong>{chain_id}</strong></article><article><label>Height</label><strong id="height">--</strong></article><article><label>Slot</label><strong id="slot">--</strong></article><article><label>Validators</label><strong id="validators">--</strong></article><article><label>Peers</label><strong id="peers">--</strong></article><article><label>Mempool</label><strong id="mempool">--</strong></article></section>
<section class="grid"><article><h3>Canonical Execution Head</h3><p id="head" class="mono">--</p><p>Proposer: <span id="proposer" class="mono">--</span></p></article><article><h3>Services</h3><div id="services"></div></article><article><h3>Finality</h3><p id="finalized" class="mono">--</p></article><article><h3>Operations</h3><p>CPU <b id="cpu">--</b></p><p>Disk write <b id="disk">--</b></p><p>Available memory <b id="memory">--</b></p></article></section>
<section class="panel"><h3>Recent Transactions</h3><table><thead><tr><th>Hash</th><th>From</th><th>To</th><th>Block</th><th>Status</th></tr></thead><tbody id="transactions"></tbody></table></section>
</main></div><script src="/frontend/assets/dashboard.js"></script></body></html>''', encoding="utf-8")
    files.append(html)

    css = assets / "dashboard.css"
    css.write_text(''':root{color-scheme:dark;--bg:#050b14;--panel:#0d1a2d;--line:#21334d;--text:#f3f7ff;--muted:#91a7c5;--green:#34d399}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 15% 0,#122a55,transparent 35%),var(--bg);color:var(--text);font:14px Inter,system-ui,sans-serif}.layout{min-height:100vh;display:grid;grid-template-columns:190px 1fr}aside{padding:24px 16px;border-right:1px solid var(--line);background:#071225}aside h2{color:#60a5fa}aside a{display:block;color:#d9e8ff;text-decoration:none;padding:10px;border-radius:8px;margin:4px 0}aside a:hover{background:#152844}main{padding:24px}header{display:flex;justify-content:space-between;align-items:center}header small,label{color:var(--muted);text-transform:uppercase;letter-spacing:.1em}#health{padding:8px 12px;border:1px solid #2a5f50;border-radius:999px;color:#bbf7d0}.kpis{display:grid;grid-template-columns:repeat(6,minmax(120px,1fr));gap:12px;margin:24px 0}.kpis article,.grid article,.panel{background:linear-gradient(180deg,#101d31,#0b1729);border:1px solid var(--line);border-radius:14px;padding:18px}.kpis strong{display:block;font-size:25px;margin-top:8px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.mono{font-family:ui-monospace,monospace;color:#7ff7cb;overflow:hidden;text-overflow:ellipsis}.service{display:inline-block;padding:6px 9px;margin:4px;border-radius:999px;background:#16372f;color:#bbf7d0}.service.off{background:#492331;color:#fecdd3}.panel{margin-top:12px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-top:1px solid var(--line)}th{color:var(--muted)}a{color:#93c5fd}@media(max-width:900px){.layout{grid-template-columns:1fr}aside{display:flex;overflow:auto;border-right:0;border-bottom:1px solid var(--line)}aside h2{display:none}aside a{white-space:nowrap}.kpis{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}}''', encoding="utf-8")
    files.append(css)

    js = assets / "dashboard.js"
    js.write_text('''const $=id=>document.getElementById(id);const n=v=>Number(v||0);const short=v=>{v=String(v||'--');return v.length>24?v.slice(0,10)+'…'+v.slice(-8):v};const bytes=v=>{v=n(v);if(!v)return '0 B';const u=['B','KB','MB','GB','TB'];let i=0;while(v>=1024&&i<u.length-1){v/=1024;i++}return v.toFixed(i?1:0)+' '+u[i]};async function get(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error(url+' '+r.status);return r.json()}function renderStatus(s){const chain=s.chain||{},head=s.head||{},beacon=s.beacon||{},m=s.monitoring||{};$('health').textContent=s.ok?'Healthy':'Degraded';$('height').textContent=chain.height??head.height??'--';$('slot').textContent=beacon.current_slot??beacon.slot??'--';$('validators').textContent=(m.validators||{}).active_count??(m.validators||{}).count??'--';$('peers').textContent=(m.peers||{}).count??(m.peers||{}).p2p_count??'--';$('mempool').textContent=(m.mempool||{}).size??((m.mempool||{}).ready_size||0)+((m.mempool||{}).queued_size||0);$('head').textContent=head.hash||chain.head||'--';$('head').title=head.hash||chain.head||'';$('proposer').textContent=short(head.proposer);$('finalized').textContent=short((beacon.finalized_checkpoint||{}).root||beacon.finalized_root);$('services').innerHTML=Object.entries(s.services||{}).map(([k,v])=>`<span class="service ${v?'':'off'}">${k}: ${v?'online':'offline'}</span>`).join('');const txs=m.recent_transactions||[];$('transactions').innerHTML=txs.slice(0,10).map(tx=>`<tr><td><a href="/tx/${tx.tx_hash||tx.hash}">${short(tx.tx_hash||tx.hash)}</a></td><td>${short(tx.from||tx.sender)}</td><td>${short(tx.to||tx.receiver)}</td><td>${tx.block_height??tx.blockNumber??'-'}</td><td>${tx.status??'observed'}</td></tr>`).join('')||'<tr><td colspan="5">Waiting for transactions</td></tr>'}function renderOps(o){const x=o.latest||o;$('cpu').textContent=n(x.host_cpu_percent).toFixed(2)+'%';$('disk').textContent=bytes(x.disk_write_bytes_per_second)+'/s';$('memory').textContent=bytes(x.available_memory_bytes)}async function refresh(){try{const [s,o]=await Promise.all([get('/api/status'),get('/api/operations/live').catch(()=>({}))]);renderStatus(s);renderOps(o)}catch(e){$('health').textContent='Disconnected';console.error(e)}}refresh();setInterval(refresh,3000);''', encoding="utf-8")
    files.append(js)

    readme = frontend / "README.md"
    readme.write_text('''# Smart Chain Frontend\n\nThis generated dashboard follows the uploaded Smart Chain frontend contract. It uses `/api/status`, `/api/operations/live`, explorer routes, validator/beacon/P2P telemetry, and `/contracts/builder`. It uses same-origin URLs so it works locally, behind a reverse proxy, or on the public RPC host without source edits.\n''', encoding="utf-8")
    files.append(readme)
