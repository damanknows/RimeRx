# RimeRx Public Demo Deployment Guide

> **Deployment Preparation, Containerization & Hosting Instructions**

---

## 1. Current Deployment Status

> [!IMPORTANT]
> **Deployment Status**: Application is fully prepared and containerized for deployment on Render, Railway, Fly.io, AWS EC2, or Azure App Service.
> No public deployment URI is claimed as live until remote cloud infrastructure provision commands are executed by the platform administrator.

---

## 2. Verified End-to-End User Flow

When deployed to production, the user flow operates as follows:

```
[ Open Production URL ]
        │
        ▼
[ Paste / Select Prescription Text ]
        │
        ▼
[ Click "Speak with Rime" ] ──► [ Hear Rime TTS Audio Stream ]
        │
        ▼
[ Click "Compare Raw vs RimeRx" ] ──► [ Side-by-Side Playback & WER/PER Metrics ]
        │
        ▼
[ Click "Run Stress Test" ] ──► [ Live ASR Closed-Loop Evaluation ]
```

---

## 3. Local Production Container Deployment (Docker)

To run the production container locally or on any server with Docker installed:

```bash
# 1. Clone repository
git clone https://github.com/damanknows/RimeRx.git
cd RimeRx

# 2. Configure environment file
cp .env.example .env
# Set RIME_API_KEY in .env

# 3. Build and launch with Docker Compose
docker-compose up --build -d

# 4. Access application at: http://localhost:8000
```

---

## 4. Cloud Deployment Setup (Render / Railway / Fly.io)

### Deployment on Render.com
1. Connect GitHub repository `damanknows/RimeRx`.
2. Select **Web Service** using `Dockerfile` (or Python Environment with command `uvicorn main:app --host 0.0.0.0 --port $PORT`).
3. Add Environment Variables:
   - `RIME_API_KEY` = `<your_production_rime_api_key>`
   - `RIME_MODEL` = `mist/v1`
   - `RIME_VOICE` = `marsh`
   - `RIME_LANGUAGE` = `en-IN`
4. Deploy service. Render automatically exposes public HTTPS URL.

---

## 5. Environment Variables Audit

| Variable | Required | Production Default | Description |
| :--- | :---: | :--- | :--- |
| `RIME_API_KEY` | **Yes** | `<secret>` | Rime TTS API authorization bearer token |
| `RIME_MODEL` | No | `mist/v1` | Production Rime TTS model |
| `RIME_VOICE` | No | `marsh` | Production Rime TTS speaker voice |
| `RIME_LANGUAGE` | No | `en-IN` | Target accent setting |
| `RIME_AUDIO_FORMAT` | No | `mp3` | Audio streaming encoding |
| `PORT` | No | `8000` | Server listening port |
