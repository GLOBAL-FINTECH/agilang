# AGILANG Suno Music Studio

A self-contained website app example for AI music generation using SunoAPI-compatible backend endpoints.

The app supports:

- Text / lyrics to full song generation
- Audio upload or browser recording
- Upload-and-cover / remix workflow
- Upload-and-extend workflow
- Editable lyrics before submission
- Genre/style prompts such as Lumba, Hip Hop, Afrobeat, Rumba, Gospel, etc.
- Status polling for generation results
- Download links for generated songs
- Vocal/instrument stem separation
- Advanced stem extraction by instrument
- Timestamped lyrics
- MIDI generation from audio
- Style boost / style refinement helper
- Webhook callback receiver for generation, stems, and MIDI jobs

> Important: only upload or remix audio/lyrics that you own or have permission to use. The UI and backend require a rights confirmation before upload or generation.

---

## Project structure

```text
examples/suno_music_app/
├─ README.md
├─ backend/
│  ├─ app.py
│  ├─ requirements.txt
│  └─ .env.example
└─ frontend/
   ├─ index.html
   ├─ styles.css
   └─ app.js
```

---

## API mapping

The backend keeps your API key private and proxies these upstream endpoints:

| Feature | Backend endpoint | Upstream endpoint |
|---|---|---|
| Upload temporary audio | `POST /api/upload` | `POST /api/file-stream-upload` on upload host |
| Generate from text/lyrics | `POST /api/generate` | `POST /api/v1/generate` |
| Upload and cover/remix | `POST /api/generate` with `sourceMode=upload-cover` | `POST /api/v1/generate/upload-cover` |
| Upload and extend | `POST /api/generate` with `sourceMode=upload-extend` | `POST /api/v1/generate/upload-extend` |
| Poll generation | `GET /api/generation/{taskId}` | `GET /api/v1/generate/record-info?taskId=...` |
| Split vocals/instruments | `POST /api/stems` | `POST /api/v1/vocal-removal/generate` |
| Poll stem results | `GET /api/stems/{taskId}` | `GET /api/v1/vocal-removal/record-info?taskId=...` |
| Timestamped lyrics | `POST /api/timestamped-lyrics` | `POST /api/v1/generate/get-timestamped-lyrics` |
| MIDI from audio | `POST /api/midi` | `POST /api/v1/midi/generate` |
| Boost style prompt | `POST /api/style/boost` | `POST /api/v1/style/generate` |
| Receive callbacks | `POST /api/callbacks/{kind}` | Your public callback URL |

---

## Local setup

From the repo root:

```bash
cd examples/suno_music_app/backend
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env    # Windows
# cp .env.example .env    # macOS/Linux
```

Edit `.env`:

```env
SUNO_API_KEY=your_real_key
PUBLIC_CALLBACK_BASE_URL=
```

For local testing you can leave `PUBLIC_CALLBACK_BASE_URL` empty and use polling from the UI. For production callbacks, set it to an HTTPS domain such as:

```env
PUBLIC_CALLBACK_BASE_URL=https://music.example.com
```

Run:

```bash
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Open:

```text
http://127.0.0.1:8000
```

---

## Main user flow

1. Choose workflow:
   - Text / lyrics to full song
   - Upload or record audio to cover/remix
   - Upload or record audio to extend
2. Add title, genre/style, mood, lyrics, and arrangement prompt.
3. Confirm that the user owns or has permission to use the audio/lyrics.
4. For upload workflows, upload a file or record audio and click **Upload to temporary file API**.
5. Click **Generate Music**.
6. Copy or keep the returned task ID and click **Poll** until status is `SUCCESS`.
7. Play/download the returned tracks.
8. Use an audio ID to split vocals/instrumental, request timestamped lyrics, or generate MIDI.

---

## Production notes

- Do not put `SUNO_API_KEY` in browser code.
- Use HTTPS for callbacks.
- Add authentication if this app is exposed publicly.
- Store completed audio files quickly because upstream temporary/generated URLs expire.
- Add database storage for users, jobs, credits, and downloads before launching commercially.
- Consider queueing long-running polling jobs with Redis/RQ/Celery or a database scheduler.
- Add moderation and legal review before accepting public uploads.

---

## Deployment idea

For a simple VPS deployment:

```bash
cd examples/suno_music_app/backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

Then place Nginx/Caddy in front of it with HTTPS and route your domain to port `8000`.
