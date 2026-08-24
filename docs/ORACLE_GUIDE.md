# Alice on Oracle Cloud — Always Free, Step by Step

The forever option: a real VM that never sleeps and keeps Alice's
memory on disk. Budget ~45 minutes. No charges — the card is only used
for identity verification.

---

## 0. What you get

| | |
|---|---|
| VM | Ampere A1 (ARM), 2 OCPU + 8 GB RAM — ~10x what Alice needs |
| Cost | ₹0 / $0 forever (Always Free tier) |
| Disk | Alice's `data/` (memory, reminders, artifacts) survives everything |
| Network | Outbound open — her web search + Wikipedia tools work |

If ARM capacity is unavailable in your region at signup time, the two
free AMD micro VMs (1 GB RAM) also run Alice comfortably.

---

## 1. Create the Oracle account

1. Go to **cloud.oracle.com** → *Start for free*.
2. Sign up with email + a credit/debit card for verification
   (a ~₹100 temporary hold, reversed — nothing is charged).
3. **Choose your home region carefully — it can never be changed.**
   Pick the one closest to you (Mumbai: *India South (Mumbai)*).
4. Finish and wait for the account to provision (minutes to a few hours).

> Tip: after the account works, you can *upgrade to Pay As You Go*
> later — the Always Free resources stay free, and the annoying
> "out of capacity" errors for ARM mostly disappear. You are only
> billed if you add resources beyond the free ones.

---

## 2. Create the VM

1. Console → hamburger menu → **Compute → Instances → Create instance**.
2. **Name**: `alice`.
3. **Image and Shape → Edit**:
   - Image: **Canonical Ubuntu 24.04** (click "Canonical Ubuntu 24.04", accept).
   - Shape: **Ampere** (VM.Standard.A1.Flex) → 2 OCPUs, 8 GB RAM.
4. Leave networking as default (*New VCN + public subnet*, "Assign a
   public IPv4 address").
5. **SSH keys — the important part**:
   - Choose *Generate a key pair*.
   - **Save Private Key** → `alice.key` and **Save Public Key** → `alice.key.pub`.
   - Keep these files forever; they are your only way in.
6. Boot volume: defaults are fine. Click **Create**.

> "Out of host capacity"? ARM is in high demand. Retry at odd hours,
> try the other Availability Domain, or temporarily create an
> E2.1.Micro (AMD) instance instead — Alice fits in it.

---

## 3. Open port 8000 in the Security List

1. Instance details → scroll to **Virtual Cloud Network** → click the VCN.
2. Left menu → **Security Lists** → *Default Security List*.
3. **Add Ingress Rules**:
   - Source CIDR: `0.0.0.0/0`
   - IP Protocol: `TCP`
   - Destination Port Range: `8000`
4. (Also add the same for `80` and `443` now — you'll want them for
   HTTPS in step 8.)

---

## 4. Log in and open the firewall inside the VM

Oracle's Ubuntu images also run their own iptables firewall — the #1
reason people see "connection refused" with everything else correct.

```bash
# on your own machine (Terminal / PowerShell)
chmod 400 alice.key
ssh -i alice.key ubuntu@<PUBLIC_IP_OF_YOUR_VM>
```

Then inside the VM:

```bash
sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
sudo netfilter-persistent save
```

---

## 5. Install Alice

```bash
sudo apt update && sudo apt install -y git python3-venv

# after merging the PR, or add: -b arena/01a03028-alice
git clone https://github.com/piyush4670/alice.git
cd alice

python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

---

## 6. Configure

```bash
cp .env.example .env
nano .env
```

Set at least:

```
API_KEY=<your free Groq key from console.groq.com>
```

(Ctrl+O, Enter to save; Ctrl+X to exit.)

Test-run once:

```bash
python -m server
# → http://<PUBLIC_IP>:8000 should show the boot screen
# stop with Ctrl+C
```

---

## 7. Make her immortal (systemd)

```bash
sudo tee /etc/systemd/system/alice.service > /dev/null <<'EOF'
[Unit]
Description=ALICE mission control
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=/home/ubuntu/alice
ExecStart=/home/ubuntu/alice/.venv/bin/python -m server
Restart=always
RestartSec=3
User=ubuntu

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now alice
```

Useful commands:

```bash
systemctl status alice        # is she up?
journalctl -u alice -f        # live logs (Ctrl+C to exit)
sudo systemctl restart alice  # after editing .env
```

---

## 8. HTTPS (needed for the microphone)

Browsers only grant mic access to secure origins, so give Alice a name:

1. **Free domain**: duckdns.org → sign in → create `yourname.duckdns.org`
   pointing at your VM's public IP.
2. **Caddy** (automatic free HTTPS):

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy

sudo tee /etc/caddy/Caddyfile > /dev/null <<'EOF'
yourname.duckdns.org {
    reverse_proxy localhost:8000
}
EOF

sudo systemctl reload caddy
```

Open **https://yourname.duckdns.org** — padlock, mic button and voice
all live. (WebSockets route through Caddy automatically.)

---

## 9. Daily life

**Update Alice** (after you merge changes into main):

```bash
cd ~/alice && git pull
sudo systemctl restart alice
```

**Her memory lives in** `~/alice/data/` — back it up occasionally:

```bash
tar czf ~/alice-backup-$(date +%F).tar.gz -C ~/alice data
```

**Reserved IP**: the public IP is "ephemeral" (changes if you
stop/start the instance). For permanence: Console → Networking →
Public IPs → *Reserve public IP* → attach it to the VM.

---

## Checklist if something doesn't work

| Symptom | Fix |
|---|---|
| SSH fails | Wrong key file / `chmod 400` missing / wrong IP |
| Page unreachable | Ingress rule (step 3) AND iptables (step 4) — both needed |
| Alice down after reboot | `sudo systemctl enable alice` |
| Mic button dead | You're on http:// not https:// (step 8) |
| "Linked brain unavailable" replies | `API_KEY` missing/invalid in `~/alice/.env`, then restart |
