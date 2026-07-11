"""Audio reader and consent-gated custom voice engine for AGILANG.

This module separates ordinary text-to-speech from custom-voice synthesis.
A custom voice profile may only be created when the speaker has provided an
explicit consent declaration.  The runtime records that declaration and adds
provenance metadata to generated audio requests.

The core package does not ship a voice-cloning model.  Instead, it offers a
provider interface so applications can use an approved local model or a remote
service through a protected backend endpoint.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from .http_query import HTTPClient, HTTPQueryError


class AudioReaderError(RuntimeError):
    """Raised when narration or custom-voice synthesis fails."""


@dataclass(slots=True)
class VoiceConsent:
    speaker_name: str
    speaker_id: str
    statement: str
    granted_at: str
    allowed_uses: list[str]
    expires_at: str | None = None

    def validate(self) -> None:
        if not self.speaker_name.strip() or not self.speaker_id.strip():
            raise AudioReaderError("speaker identity is required")
        if len(self.statement.strip()) < 20:
            raise AudioReaderError("consent statement is too short")
        if "voice" not in self.statement.lower():
            raise AudioReaderError("consent statement must explicitly mention voice use")
        if not self.allowed_uses:
            raise AudioReaderError("at least one allowed use is required")


@dataclass(slots=True)
class VoiceProfile:
    id: str
    display_name: str
    speaker_id: str
    reference_audio_sha256: str
    consent_sha256: str
    created_at: str
    provider: str
    provider_voice_id: str | None = None
    disclosure_required: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NarrationRequest:
    text: str
    voice: str | None = None
    language: str = "en"
    rate: float = 1.0
    pitch: float = 1.0
    output_format: str = "mp3"
    disclose_synthetic_voice: bool = True

    def validate(self) -> None:
        if not self.text.strip():
            raise AudioReaderError("narration text is required")
        if len(self.text) > 100_000:
            raise AudioReaderError("narration text exceeds 100000 characters")
        if not 0.5 <= float(self.rate) <= 2.0:
            raise AudioReaderError("rate must be between 0.5 and 2.0")
        if not 0.5 <= float(self.pitch) <= 2.0:
            raise AudioReaderError("pitch must be between 0.5 and 2.0")
        if self.output_format not in {"mp3", "wav", "ogg"}:
            raise AudioReaderError("unsupported output format")


class VoiceProvider(Protocol):
    name: str

    def create_voice(self, *, reference_audio: bytes, consent: VoiceConsent, display_name: str) -> str:
        ...

    def synthesize(self, request: NarrationRequest, *, provider_voice_id: str | None = None) -> bytes:
        ...


class RemoteVoiceProvider:
    """Provider adapter for a protected TTS/custom-voice HTTP endpoint.

    The endpoint is expected to enforce its own authentication and consent
    controls.  It must return JSON containing either `audio_base64` or an
    `audio_url`.  Cloudflare Workers can be used as the gateway even when the
    underlying speech model is hosted elsewhere.
    """

    name = "remote"

    def __init__(self, endpoint: str, *, bearer_token: str, timeout: float = 60.0, allow_private: bool = False) -> None:
        if not bearer_token:
            raise ValueError("bearer_token is required")
        self.endpoint = endpoint.rstrip("/")
        self.token = bearer_token
        self.client = HTTPClient(timeout=timeout, retries=1, max_response_bytes=32 * 1024 * 1024, allow_private=allow_private)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def create_voice(self, *, reference_audio: bytes, consent: VoiceConsent, display_name: str) -> str:
        consent.validate()
        payload = {
            "display_name": display_name,
            "reference_audio_base64": base64.b64encode(reference_audio).decode("ascii"),
            "consent": asdict(consent),
            "provenance": {"source": "agilang", "synthetic_voice": True},
        }
        response = self.client.post(f"{self.endpoint}/voices", json_body=payload, headers=self._headers())
        if not response.ok:
            raise AudioReaderError(f"voice provider rejected profile creation: HTTP {response.status}")
        data = response.json()
        voice_id = data.get("voice_id") if isinstance(data, dict) else None
        if not voice_id:
            raise AudioReaderError("voice provider did not return voice_id")
        return str(voice_id)

    def synthesize(self, request: NarrationRequest, *, provider_voice_id: str | None = None) -> bytes:
        request.validate()
        payload = {
            "text": request.text,
            "voice_id": provider_voice_id or request.voice,
            "language": request.language,
            "rate": request.rate,
            "pitch": request.pitch,
            "format": request.output_format,
            "disclosure": "synthetic voice" if request.disclose_synthetic_voice else None,
            "provenance": {"source": "agilang", "synthetic_voice": bool(provider_voice_id)},
        }
        response = self.client.post(f"{self.endpoint}/synthesize", json_body=payload, headers=self._headers())
        if not response.ok:
            raise AudioReaderError(f"voice synthesis failed: HTTP {response.status}")
        data = response.json()
        if isinstance(data, dict) and data.get("audio_base64"):
            return base64.b64decode(data["audio_base64"], validate=True)
        if isinstance(data, dict) and data.get("audio_url"):
            try:
                audio_response = self.client.get(str(data["audio_url"]))
            except HTTPQueryError as exc:
                raise AudioReaderError(str(exc)) from exc
            if not audio_response.ok:
                raise AudioReaderError(f"audio download failed: HTTP {audio_response.status}")
            return audio_response.body
        raise AudioReaderError("voice provider returned no audio")


class AudioReader:
    def __init__(self, provider: VoiceProvider, *, profile_dir: str | Path = "storage/voices") -> None:
        self.provider = provider
        self.profile_dir = Path(profile_dir)
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def create_voice_profile(self, *, display_name: str, reference_audio: bytes, consent: VoiceConsent) -> VoiceProfile:
        consent.validate()
        if len(reference_audio) < 1024:
            raise AudioReaderError("reference audio is too small")
        if len(reference_audio) > 25 * 1024 * 1024:
            raise AudioReaderError("reference audio exceeds 25 MB")
        safe_name = re.sub(r"[^A-Za-z0-9_. -]+", "", display_name).strip()
        if not safe_name:
            raise AudioReaderError("display name is invalid")

        provider_voice_id = self.provider.create_voice(reference_audio=reference_audio, consent=consent, display_name=safe_name)
        consent_json = json.dumps(asdict(consent), sort_keys=True, separators=(",", ":")).encode("utf-8")
        profile = VoiceProfile(
            id=f"voice_{uuid.uuid4().hex}",
            display_name=safe_name,
            speaker_id=consent.speaker_id,
            reference_audio_sha256=hashlib.sha256(reference_audio).hexdigest(),
            consent_sha256=hashlib.sha256(consent_json).hexdigest(),
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            provider=self.provider.name,
            provider_voice_id=provider_voice_id,
        )
        path = self.profile_dir / f"{profile.id}.json"
        path.write_text(json.dumps(profile.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return profile

    def load_profile(self, profile_id: str) -> VoiceProfile:
        if not re.fullmatch(r"voice_[0-9a-f]{32}", profile_id):
            raise AudioReaderError("invalid voice profile id")
        path = self.profile_dir / f"{profile_id}.json"
        if not path.exists():
            raise AudioReaderError("voice profile not found")
        return VoiceProfile(**json.loads(path.read_text(encoding="utf-8")))

    def narrate(self, request: NarrationRequest, *, profile: VoiceProfile | None = None, output_path: str | Path | None = None) -> bytes:
        request.validate()
        provider_voice_id = profile.provider_voice_id if profile else None
        audio = self.provider.synthesize(request, provider_voice_id=provider_voice_id)
        if not audio:
            raise AudioReaderError("provider returned empty audio")
        if output_path is not None:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(audio)
        return audio


def browser_speech_script(element_id: str = "lesson-content", *, language: str = "en-ZM", rate: float = 0.9) -> str:
    """Return a dependency-free browser speech-synthesis controller.

    This is ordinary device text-to-speech; it does not clone a person's voice.
    """
    return f"""
<script>
(() => {{
  const target = () => document.getElementById({json.dumps(element_id)});
  let utterance = null;
  window.agilangAudioReader = {{
    play() {{
      const node = target();
      if (!node || !window.speechSynthesis) return false;
      window.speechSynthesis.cancel();
      utterance = new SpeechSynthesisUtterance(node.innerText || node.textContent || "");
      utterance.lang = {json.dumps(language)};
      utterance.rate = {float(rate)};
      window.speechSynthesis.speak(utterance);
      return true;
    }},
    pause() {{ window.speechSynthesis && window.speechSynthesis.pause(); }},
    resume() {{ window.speechSynthesis && window.speechSynthesis.resume(); }},
    stop() {{ window.speechSynthesis && window.speechSynthesis.cancel(); }}
  }};
}})();
</script>
""".strip()
