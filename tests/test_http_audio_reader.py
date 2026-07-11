from __future__ import annotations

import json
from pathlib import Path

import pytest

from agilang.audio_reader import AudioReader, AudioReaderError, NarrationRequest, VoiceConsent, browser_speech_script
from agilang.http_query import HTTPClient, HTTPQueryError, HTTPResponse


class FakeVoiceProvider:
    name = "fake"

    def create_voice(self, *, reference_audio: bytes, consent: VoiceConsent, display_name: str) -> str:
        consent.validate()
        assert reference_audio
        assert display_name
        return "provider_voice_1"

    def synthesize(self, request: NarrationRequest, *, provider_voice_id: str | None = None) -> bytes:
        request.validate()
        return b"FAKE-AUDIO:" + request.text.encode("utf-8")


def valid_consent() -> VoiceConsent:
    return VoiceConsent(
        speaker_name="Test Speaker",
        speaker_id="speaker-001",
        statement="I explicitly consent to my voice being used for educational narration.",
        granted_at="2026-07-11T00:00:00Z",
        allowed_uses=["education"],
    )


def test_http_response_json_and_dict():
    response = HTTPResponse(
        status=200,
        headers={"content-type": "application/json; charset=utf-8"},
        body=b'{"ok":true}',
        url="https://example.com",
        elapsed_ms=4.5,
    )
    assert response.ok is True
    assert response.json() == {"ok": True}
    assert response.as_dict()["json"] == {"ok": True}


def test_http_client_rejects_non_http_scheme():
    client = HTTPClient()
    with pytest.raises(HTTPQueryError):
        client.get("file:///etc/passwd")


def test_http_client_rejects_loopback_by_default():
    client = HTTPClient()
    with pytest.raises(HTTPQueryError):
        client.get("http://127.0.0.1:8080")


def test_http_client_allows_private_when_explicit(monkeypatch):
    client = HTTPClient(allow_private=True)
    client._validate_url("http://127.0.0.1:8080")


def test_voice_consent_is_mandatory(tmp_path: Path):
    reader = AudioReader(FakeVoiceProvider(), profile_dir=tmp_path)
    consent = VoiceConsent(
        speaker_name="Test",
        speaker_id="speaker-1",
        statement="I agree.",
        granted_at="2026-07-11T00:00:00Z",
        allowed_uses=["education"],
    )
    with pytest.raises(AudioReaderError):
        reader.create_voice_profile(display_name="Teacher", reference_audio=b"x" * 2048, consent=consent)


def test_create_load_and_use_voice_profile(tmp_path: Path):
    reader = AudioReader(FakeVoiceProvider(), profile_dir=tmp_path)
    profile = reader.create_voice_profile(
        display_name="Teacher Voice",
        reference_audio=b"reference-audio" * 200,
        consent=valid_consent(),
    )
    assert profile.provider_voice_id == "provider_voice_1"
    loaded = reader.load_profile(profile.id)
    assert loaded.reference_audio_sha256 == profile.reference_audio_sha256

    output = tmp_path / "lesson.mp3"
    audio = reader.narrate(NarrationRequest(text="Welcome to AGILANG"), profile=loaded, output_path=output)
    assert audio.startswith(b"FAKE-AUDIO:")
    assert output.read_bytes() == audio


def test_narration_validation():
    with pytest.raises(AudioReaderError):
        NarrationRequest(text="", rate=1.0).validate()
    with pytest.raises(AudioReaderError):
        NarrationRequest(text="hello", rate=4.0).validate()


def test_browser_speech_script_contains_controls():
    script = browser_speech_script("lesson")
    assert "speechSynthesis" in script
    assert "play()" in script
    assert "pause()" in script
    assert "resume()" in script
    assert "stop()" in script
