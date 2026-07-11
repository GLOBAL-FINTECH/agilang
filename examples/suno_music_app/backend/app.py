from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, HttpUrl, field_validator

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
CALLBACK_STORE = BASE_DIR / "callbacks.json"

SUNO_API_BASE = os.getenv("SUNO_API_BASE", "https://api.sunoapi.org").rstrip("/")
SUNO_UPLOAD_BASE = os.getenv("SUNO_UPLOAD_BASE", "https://sunoapiorg.redpandaai.co").rstrip("/")
PUBLIC_CALLBACK_BASE_URL = os.getenv("PUBLIC_CALLBACK_BASE_URL", "").rstrip("/")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(60 * 1024 * 1024)))
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
    if origin.strip()
]

app = FastAPI(
    title="AGILANG Suno Music Studio API",
    version="1.0.0",
    description="A secure backend proxy for text-to-music, upload remix/cover, extension, lyrics, MIDI, and stem separation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ModelName = Literal["V4", "V4_5", "V4_5PLUS", "V4_5ALL", "V5", "V5_5"]
SourceMode = Literal["text", "upload-cover", "upload-extend"]
StemType = Literal["separate_vocal", "split_stem", "split_stem_advanced"]

SUPPORTED_STEMS = {
    "Lead Vocal",
    "Drum Kit",
    "Kick",
    "Snare",
    "Bass",
    "Backing Vocals",
    "Piano",
    "Electric Guitar",
    "Percussion",
    "String Section",
    "Synth",
    "Acoustic Guitar",
    "Sound Effects",
    "Synth Pad",
    "Synth Bass",
    "Guitar",
    "Brass Section",
    "Organ",
    "Electronic Drum Kit",
    "Lead Electric Guitar",
    "Synth Keys",
    "Rhythm Electric Guitar",
    "Electric Piano",
    "Upright Bass",
    "Keyboards",
    "Woodwinds",
    "Flute",
    "Trumpet",
    "Violin",
    "Choir",
    "Banjo",
    "Saxophone",
    "Orchestra",
    "Horns",
    "Cymbals",
    "Hand Clap",
    "Congas",
    "Drone",
    "Cello",
    "Harmonica",
    "Marimba",
    "Vibraphone",
    "Tuba",
    "808",
    "Hi-Hat",
}


def _api_key() -> str:
    key = os.getenv("SUNO_API_KEY", "").strip()
    if not key or key == "replace_with_your_sunoapi_key":
        raise HTTPException(status_code=500, detail="SUNO_API_KEY is missing. Copy .env.example to .env and set it.")
    return key


def _json_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_api_key()}"}


def _callback_url(kind: str, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    if PUBLIC_CALLBACK_BASE_URL:
        return f"{PUBLIC_CALLBACK_BASE_URL}/api/callbacks/{kind}"
    # The upstream API requires a callback URL. For local development, replace this with a public ngrok/cloudflared URL.
    return "https://example.com/api/callbacks/suno"


def _safe_filename(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return name or "audio-upload.wav"


def _call_suno_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{SUNO_API_BASE}{path}"
    try:
        response = requests.post(url, json=payload, headers=_json_headers(), timeout=120)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Suno API request failed: {exc}") from exc
    return _parse_upstream_response(response)


def _call_suno_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{SUNO_API_BASE}{path}"
    try:
        response = requests.get(url, params=params or {}, headers=_auth_headers(), timeout=60)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Suno API request failed: {exc}") from exc
    return _parse_upstream_response(response)


def _parse_upstream_response(response: requests.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail={"message": "Upstream returned non-JSON response", "text": response.text}) from exc

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=body)

    if isinstance(body, dict) and body.get("code") not in (None, 200):
        raise HTTPException(status_code=400, detail=body)

    return body


def _persist_callback(kind: str, payload: dict[str, Any]) -> None:
    record = {
        "kind": kind,
        "receivedAt": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    existing: list[dict[str, Any]] = []
    if CALLBACK_STORE.exists():
        try:
            existing = json.loads(CALLBACK_STORE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []
    existing.append(record)
    CALLBACK_STORE.write_text(json.dumps(existing[-200:], indent=2), encoding="utf-8")


def _compact_style(req: "GenerateRequest") -> str:
    parts = [req.genre]
    if req.mood:
        parts.append(req.mood)
    if req.extraStyle:
        parts.append(req.extraStyle)
    style = ", ".join(part.strip() for part in parts if part and part.strip())
    limit = 200 if req.model == "V4" else 1000
    return style[:limit]


def _optional_float(name: str, value: float | None, payload: dict[str, Any]) -> None:
    if value is not None:
        if not 0 <= value <= 1:
            raise HTTPException(status_code=422, detail=f"{name} must be between 0 and 1")
        payload[name] = value


class GenerateRequest(BaseModel):
    sourceMode: SourceMode = "text"
    uploadUrl: HttpUrl | None = None
    rightsConfirmed: bool = False
    customMode: bool = True
    instrumental: bool = False
    model: ModelName = "V4_5ALL"
    title: str = Field(default="Untitled Track", max_length=100)
    prompt: str | None = Field(default=None, max_length=5000)
    lyrics: str | None = Field(default=None, max_length=5000)
    genre: str = Field(default="Afrobeat", max_length=1000)
    mood: str | None = Field(default=None, max_length=300)
    extraStyle: str | None = Field(default=None, max_length=1000)
    negativeTags: str | None = Field(default=None, max_length=500)
    vocalGender: Literal["m", "f"] | None = None
    personaId: str | None = None
    personaModel: Literal["style_persona", "voice_persona"] | None = None
    styleWeight: float | None = None
    weirdnessConstraint: float | None = None
    audioWeight: float | None = None
    callBackUrl: HttpUrl | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title is required")
        return cleaned[:100]


class StemRequest(BaseModel):
    taskId: str = Field(..., min_length=4)
    audioId: str = Field(..., min_length=4)
    type: StemType = "separate_vocal"
    stemName: str | None = None
    callBackUrl: HttpUrl | None = None

    @field_validator("stemName")
    @classmethod
    def validate_stem(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        cleaned = value.strip()
        if cleaned not in SUPPORTED_STEMS:
            raise ValueError(f"Unsupported stemName: {cleaned}")
        return cleaned


class AudioActionRequest(BaseModel):
    taskId: str = Field(..., min_length=4)
    audioId: str = Field(..., min_length=4)
    callBackUrl: HttpUrl | None = None


class StyleBoostRequest(BaseModel):
    content: str = Field(..., min_length=2, max_length=1000)


class LyricsGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=2, max_length=1000)
    callBackUrl: HttpUrl | None = None


def build_generation_payload(req: GenerateRequest) -> tuple[str, dict[str, Any]]:
    if not req.rightsConfirmed:
        raise HTTPException(
            status_code=422,
            detail="Confirm that you own or have permission to use the uploaded audio/lyrics before generating.",
        )

    endpoint = {
        "text": "/api/v1/generate",
        "upload-cover": "/api/v1/generate/upload-cover",
        "upload-extend": "/api/v1/generate/upload-extend",
    }[req.sourceMode]

    payload: dict[str, Any] = {
        "customMode": req.customMode,
        "instrumental": req.instrumental,
        "model": req.model,
        "callBackUrl": _callback_url("suno", str(req.callBackUrl) if req.callBackUrl else None),
    }

    if req.sourceMode != "text":
        if not req.uploadUrl:
            raise HTTPException(status_code=422, detail="uploadUrl is required for upload-cover and upload-extend modes")
        payload["uploadUrl"] = str(req.uploadUrl)

    if req.customMode:
        payload["style"] = _compact_style(req)
        payload["title"] = req.title[:80] if req.model in {"V4", "V4_5ALL"} else req.title[:100]
        if not req.instrumental:
            lyric_text = (req.lyrics or req.prompt or "").strip()
            if not lyric_text:
                raise HTTPException(status_code=422, detail="lyrics or prompt is required when customMode=true and instrumental=false")
            payload["prompt"] = lyric_text[:3000] if req.model == "V4" else lyric_text[:5000]
    else:
        non_custom_prompt = (req.prompt or req.lyrics or f"Create a {req.genre} song called {req.title}").strip()
        payload["prompt"] = non_custom_prompt[:500]

    for key in ("negativeTags", "vocalGender", "personaId", "personaModel"):
        value = getattr(req, key)
        if value:
            payload[key] = value

    _optional_float("styleWeight", req.styleWeight, payload)
    _optional_float("weirdnessConstraint", req.weirdnessConstraint, payload)
    _optional_float("audioWeight", req.audioWeight, payload)

    return endpoint, payload


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "agilang-suno-music-app",
        "sunoApiBase": SUNO_API_BASE,
        "sunoUploadBase": SUNO_UPLOAD_BASE,
        "callbackConfigured": bool(PUBLIC_CALLBACK_BASE_URL),
    }


@app.post("/api/upload")
def upload_audio(
    file: UploadFile = File(...),
    rightsConfirmed: bool = Form(False),
) -> dict[str, Any]:
    if not rightsConfirmed:
        raise HTTPException(status_code=422, detail="You must confirm you own or have permission to use this audio.")

    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Upload exceeds {MAX_UPLOAD_BYTES} bytes")

    filename = _safe_filename(file.filename or "audio-upload.wav")
    files = {"file": (filename, content, file.content_type or "application/octet-stream")}
    data = {"uploadPath": "audio/user-uploads", "fileName": filename}

    try:
        response = requests.post(
            f"{SUNO_UPLOAD_BASE}/api/file-stream-upload",
            data=data,
            files=files,
            headers=_auth_headers(),
            timeout=180,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Upload API request failed: {exc}") from exc

    return _parse_upstream_response(response)


@app.post("/api/generate")
def generate_music(req: GenerateRequest) -> dict[str, Any]:
    endpoint, payload = build_generation_payload(req)
    upstream = _call_suno_post(endpoint, payload)
    return {"endpoint": endpoint, "payloadSent": payload, "upstream": upstream}


@app.get("/api/generation/{task_id}")
def generation_status(task_id: str) -> dict[str, Any]:
    return _call_suno_get("/api/v1/generate/record-info", {"taskId": task_id})


@app.post("/api/stems")
def split_stems(req: StemRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "taskId": req.taskId,
        "audioId": req.audioId,
        "type": req.type,
        "callBackUrl": _callback_url("stems", str(req.callBackUrl) if req.callBackUrl else None),
    }
    if req.type == "split_stem_advanced":
        if not req.stemName:
            raise HTTPException(status_code=422, detail="stemName is required for split_stem_advanced")
        payload["stemName"] = req.stemName
    return _call_suno_post("/api/v1/vocal-removal/generate", payload)


@app.get("/api/stems/{task_id}")
def stem_status(task_id: str) -> dict[str, Any]:
    return _call_suno_get("/api/v1/vocal-removal/record-info", {"taskId": task_id})


@app.post("/api/timestamped-lyrics")
def timestamped_lyrics(req: AudioActionRequest) -> dict[str, Any]:
    return _call_suno_post("/api/v1/generate/get-timestamped-lyrics", req.model_dump(exclude_none=True))


@app.post("/api/midi")
def generate_midi(req: AudioActionRequest) -> dict[str, Any]:
    payload = req.model_dump(exclude_none=True)
    payload["callBackUrl"] = _callback_url("midi", str(req.callBackUrl) if req.callBackUrl else None)
    return _call_suno_post("/api/v1/midi/generate", payload)


@app.post("/api/style/boost")
def boost_style(req: StyleBoostRequest) -> dict[str, Any]:
    return _call_suno_post("/api/v1/style/generate", {"content": req.content})


@app.post("/api/callbacks/{kind}")
def receive_callback(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    _persist_callback(kind, payload)
    return {"ok": True}


@app.get("/api/callbacks")
def list_callbacks() -> list[dict[str, Any]]:
    if not CALLBACK_STORE.exists():
        return []
    try:
        return json.loads(CALLBACK_STORE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


@app.get("/")
def index() -> FileResponse:
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(index_file)
