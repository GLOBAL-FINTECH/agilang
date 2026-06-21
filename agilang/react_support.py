"""React web/mobile scaffolding helpers for AGILANG."""

from __future__ import annotations

import json
from pathlib import Path

AGILANG_CLIENT_TS = """
export type AgiEvent = { id?: string; type: string; topic?: string; payload?: any; ts?: string };

export class AgiRealtimeClient {
  private ws?: WebSocket;
  private listeners: Map<string, Set<(event: AgiEvent) => void>> = new Map();
  constructor(public url: string) {}
  connect() {
    this.ws = new WebSocket(this.url);
    this.ws.onmessage = (message) => {
      const event = JSON.parse(message.data) as AgiEvent;
      const handlers = [...(this.listeners.get(event.type) || []), ...(this.listeners.get('*') || [])];
      handlers.forEach((handler) => handler(event));
    };
  }
  on(type: string, handler: (event: AgiEvent) => void) {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)!.add(handler);
    return () => this.listeners.get(type)!.delete(handler);
  }
  send(type: string, payload: any = {}, topic?: string) {
    this.ws?.send(JSON.stringify({ type, payload, topic }));
  }
  close() { this.ws?.close(); }
}

export class AgiWebRTCSignaling {
  constructor(public realtime: AgiRealtimeClient, public peerId: string, public room: string) {}
  join(token?: string) { this.realtime.send('webrtc.join', { peer_id: this.peerId, room: this.room, token }); }
  offer(to: string, sdp: string) { this.realtime.send('webrtc.offer', { sdp, to, from: this.peerId, room: this.room }); }
  answer(to: string, sdp: string) { this.realtime.send('webrtc.answer', { sdp, to, from: this.peerId, room: this.room }); }
  ice(to: string, candidate: RTCIceCandidateInit) { this.realtime.send('webrtc.ice', { candidate, to, from: this.peerId, room: this.room }); }
}
""".strip()

WEB_APP_TSX = """
import { useEffect, useRef, useState } from 'react';
import { AgiRealtimeClient, AgiEvent } from './agilangClient';
import './App.css';

export default function App() {
  const [events, setEvents] = useState<AgiEvent[]>([]);
  const clientRef = useRef<AgiRealtimeClient | null>(null);

  useEffect(() => {
    const client = new AgiRealtimeClient(import.meta.env.VITE_AGILANG_WS || 'ws://127.0.0.1:9000/realtime');
    client.on('*', event => setEvents(prev => [event, ...prev].slice(0, 20)));
    client.connect();
    clientRef.current = client;
    return () => client.close();
  }, []);

  return (
    <main className="shell">
      <section className="card">
        <p className="eyebrow">AGILANG + React</p>
        <h1>Secure realtime dashboard</h1>
        <p>Connect this app to an AGILANG WebSocket or WebRTC signaling server.</p>
        <button onClick={() => clientRef.current?.send('dashboard.ping', { source: 'react' }, 'dashboard')}>Send ping</button>
      </section>
      <section className="feed">
        {events.map((event, index) => <pre key={event.id || index}>{JSON.stringify(event, null, 2)}</pre>)}
      </section>
    </main>
  );
}
""".strip()

AGILANG_NATIVE_RUNTIME_TS = """
import { NativeModules, Platform } from 'react-native';

export type AgiNativeRuntimeStatus = {
  platform: string;
  available: boolean;
  version?: string;
  capabilities?: any;
};

export function agiNativeRuntimeStatus(): AgiNativeRuntimeStatus {
  const mod = NativeModules.AgilangRuntimeModule;
  if (!mod) return { platform: Platform.OS, available: false };
  try {
    const version = mod.nativeVersion?.();
    const raw = mod.nativeCapabilities?.() || '{}';
    return { platform: Platform.OS, available: true, version, capabilities: JSON.parse(raw) };
  } catch {
    return { platform: Platform.OS, available: false };
  }
}
""".strip()

MOBILE_APP_TSX = """
import { useEffect, useRef, useState } from 'react';
import { Text, View, Button, ScrollView, StyleSheet } from 'react-native';
import { AgiRealtimeClient, AgiEvent } from './src/agilangClient';

export default function App() {
  const [events, setEvents] = useState<AgiEvent[]>([]);
  const client = useRef<AgiRealtimeClient | null>(null);
  useEffect(() => {
    const c = new AgiRealtimeClient(process.env.EXPO_PUBLIC_AGILANG_WS || 'ws://127.0.0.1:9000/realtime');
    c.on('*', event => setEvents(prev => [event, ...prev].slice(0, 20)));
    c.connect();
    client.current = c;
    return () => c.close();
  }, []);
  return <View style={styles.container}><Text style={styles.title}>AGILANG Mobile</Text><Button title="Send ping" onPress={() => client.current?.send('mobile.ping', { source: 'expo' }, 'mobile')} /><ScrollView>{events.map((e, i) => <Text key={i} style={styles.event}>{JSON.stringify(e)}</Text>)}</ScrollView></View>;
}
const styles = StyleSheet.create({ container: { flex: 1, padding: 32, paddingTop: 64 }, title: { fontSize: 28, fontWeight: '700', marginBottom: 12 }, event: { padding: 8, marginTop: 8, backgroundColor: '#eef2ff' } });
""".strip()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def create_react_web_project(name: str, root: str | Path | None = None) -> Path:
    project = Path(root or ".").resolve() / name
    project.mkdir(parents=True, exist_ok=True)
    _write(project / "package.json", json.dumps({
        "scripts": {"dev": "vite --host 0.0.0.0", "build": "vite build", "preview": "vite preview"},
        "dependencies": {"@vitejs/plugin-react": "latest", "vite": "latest", "typescript": "latest", "react": "latest", "react-dom": "latest"},
        "devDependencies": {}
    }, indent=2))
    _write(project / "index.html", '<div id="root"></div><script type="module" src="/src/main.tsx"></script>')
    _write(project / "src/main.tsx", "import React from 'react';\nimport { createRoot } from 'react-dom/client';\nimport App from './App';\ncreateRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);")
    _write(project / "src/App.tsx", WEB_APP_TSX)
    _write(project / "src/agilangClient.ts", AGILANG_CLIENT_TS)
    _write(project / "src/agilangNativeRuntime.ts", AGILANG_NATIVE_RUNTIME_TS)
    _write(project / "src/App.css", ".shell{min-height:100vh;padding:48px;font-family:Inter,system-ui;background:#0f172a;color:white}.card{max-width:760px;padding:32px;border-radius:24px;background:rgba(255,255,255,.08)}button{padding:12px 18px;border:0;border-radius:12px}.feed pre{white-space:pre-wrap;background:#111827;padding:16px;border-radius:16px}")
    _write(project / ".env.example", "VITE_AGILANG_WS=ws://127.0.0.1:9000/realtime")
    _write(project / "README.md", "# AGILANG React Web Client\n\nRun `npm install` then `npm run dev`. Set `VITE_AGILANG_WS` to your AGILANG WebSocket endpoint.")
    return project


def create_react_mobile_project(name: str, root: str | Path | None = None) -> Path:
    project = Path(root or ".").resolve() / name
    project.mkdir(parents=True, exist_ok=True)
    _write(project / "package.json", json.dumps({
        "scripts": {"start": "expo start", "android": "expo start --android", "ios": "expo start --ios", "web": "expo start --web"},
        "dependencies": {"expo": "latest", "react": "latest", "react-native": "latest"},
        "devDependencies": {"typescript": "latest"}
    }, indent=2))
    _write(project / "App.tsx", MOBILE_APP_TSX)
    _write(project / "src/agilangClient.ts", AGILANG_CLIENT_TS)
    _write(project / "src/agilangNativeRuntime.ts", AGILANG_NATIVE_RUNTIME_TS)
    _write(project / "app.json", json.dumps({"expo": {"name": name, "slug": name, "scheme": name.replace('_','-')}} , indent=2))
    _write(project / ".env.example", "EXPO_PUBLIC_AGILANG_WS=ws://127.0.0.1:9000/realtime")
    _write(project / "README.md", "# AGILANG React Native / Expo Client\n\nRun `npm install` then `npm run start`. Set `EXPO_PUBLIC_AGILANG_WS` to your AGILANG endpoint.\n\n## Optional native runtime bridge\n\nGenerate Android/iOS bridge source with:\n\n```bash\nagi mobile native-bridge " + name + "-native --target both\n```\n\nThe Expo/React Native app works without the native bridge; the bridge is for linking the AGILANG C networking runtime into native Android/iOS builds.")
    return project


def write_react_sdk(directory: str | Path) -> Path:
    out = Path(directory).resolve()
    out.mkdir(parents=True, exist_ok=True)
    _write(out / "agilangClient.ts", AGILANG_CLIENT_TS)
    return out / "agilangClient.ts"


__all__ = ["create_react_web_project", "create_react_mobile_project", "write_react_sdk"]
