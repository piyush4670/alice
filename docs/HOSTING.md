# Hosting Alice for Free

Alice is a standard FastAPI app that binds to `0.0.0.0` and honours the
platform-injected `PORT` (or `ALICE_PORT`), serves her own UI, and has a
`/api/health` endpoint — so she deploys almost anywhere. Pick a tier below.

| Host | Free? | Sleeps? | Memory survives? | WebSockets |
|---|---|---|---|---|
| Hugging Face Spaces (Docker) | yes | after ~48h idle | no (wipes on restart) | yes |
| Render (Web Service) | yes | after 15m idle | no (ephemeral disk) | yes |
| Koyeb | one free service | no | no (ephemeral disk) | yes |
| Oracle Cloud Always Free VM | forever | never | **yes** | yes |
| Your PC + Cloudflare Tunnel | yes | when PC is off | **yes** | yes |

The AI brain is free either way: Groq's free-tier key covers the linked
brain; without a key Alice runs her offline core.

---

## Option 1 — Render (easiest, deploys straight from GitHub)

1. Push this repo to GitHub.
2. render.com → **New → Web Service** → connect the repo.
3. Build command: `pip install -r requirements.txt`
   Start command: `python -m server`
4. Add the secret env var `API_KEY` (your free Groq key). Leave `PORT`
   alone — Render injects it and Alice picks it up automatically.
5. Free instance: sleeps after 15 minutes of inactivity (first visit
   after that takes ~30–60s to wake). Ping `https://<your-app>.onrender.com/api/health`
   with a free cron (cron-job.org, every 10 min) to keep her awake.

## Option 2 — Hugging Face Spaces (Docker)

1. huggingface.co → **New Space** → SDK: **Docker**.
2. Push this repo to the Space (the included `Dockerfile` is already
   HF-ready: non-root user, port 7860, `/data` volume target).
3. Space → **Settings → Variables and secrets** → add `API_KEY`.
4. Your URL: `https://<your-name>-alice.hf.space`

Spaces sleep after ~48h idle and reset storage on restart.

## Option 3 — Koyeb (one always-on free service)

1. koyeb.com → **Create Service** → GitHub repo.
2. Builder: Dockerfile (already included).
3. Add `API_KEY` as a secret. Deploy.

## Option 4 — Oracle Cloud Always Free VM (always on + persistent)

The only "forever free" tier with a real, persistent disk — the right
home if Alice is your long-term assistant.

1. Create an Always Free VM (Ampere A1, any shape up to 4 cores/24GB).
2. `sudo apt update && sudo apt install -y python3-venv git`
3. `git clone <your-repo> && cd alice`
4. `python3 -m venv .venv && . .venv/bin/activate`
5. `pip install -r requirements.txt`
6. `cp .env.example .env` — add your `API_KEY`, set `ALICE_PORT=8000`
7. Keep it alive with systemd:

```ini
# /etc/systemd/system/alice.service
[Unit]
Description=ALICE mission control
After=network-online.target

[Service]
WorkingDirectory=/home/ubuntu/alice
ExecStart=/home/ubuntu/alice/.venv/bin/python -m server
Restart=always
User=ubuntu

[Install]
WantedBy=multi-user.target
```

`sudo systemctl enable --now alice`, then open `http://<vm-ip>:8000`
(open port 8000 in the VM's security list). Add HTTPS with a free
Cloudflare proxy or Caddy — required for the microphone to work, since
browsers only allow mic access on secure origins.

## Option 5 — Your own machine + Cloudflare Tunnel

Free, persistent, private:

```bash
# with the server running locally on :8000
cloudflared tunnel --url http://localhost:8000
```

---

## Two honest warnings

**Ephemeral memory.** Free tiers (Render, HF, Koyeb) wipe the
filesystem on every restart: Alice's `data/` (facts, notes, reminders,
artifacts) resets. Fine for demoing; for an assistant that truly
remembers you, use Oracle VM / home hosting, or ask for a hosted-database
storage backend.

**Public URL = public Alice.** Anyone with the link can talk to her and
use her tools. Before sharing, add an access passcode (`ALICE_PASSCODE`)
— a small gate in the WebSocket handshake — or keep the URL private.
