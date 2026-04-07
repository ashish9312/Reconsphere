# 🛡️ Reconsphere: AI-Powered OSINT & Cyber Intelligence

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit)
![License](https://img.shields.io/badge/License-Academic%20%2F%20Research-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

**Reconsphere** is a powerful, real-time Open Source Intelligence (OSINT) and cyber-intelligence platform. It combines **AI-based facial recognition**, **reverse image search**, **email & phone breach detection**, and **dark web scanning** — all served through a clean, browser-based Streamlit interface.

> Built as an MCA Major Project by Ashish. Ideal for cybersecurity students, researchers, and ethical investigators.

---

## 📖 What is Reconsphere?

In today's digital world, personal information spreads across hundreds of websites, data-breach archives, and even the dark web. **Reconsphere** gives you a single unified dashboard to:

- **Find faces** — Upload a photo and discover matching images across the internet using AI face-comparison and reverse image search.
- **Detect data leaks** — Check whether an email address or phone number has appeared in known breach databases.
- **Explore the dark web** — Scan `.onion` mirrors (via Tor) for mentions of leaked data.
- **Work offline** — Use the bundled `leak_database.json` for demos and testing without any live API calls.

---

## 🚀 Features

| Module | Description |
|--------|-------------|
| **🖼️ FaceRecon** | Upload a face photo and find matching profiles across Reddit, Pinterest, Bing using reverse image search + AI-based face matching. |
| **📧 Email Leak Checker** | Enter an email and scan HaveIBeenPwned (HIBP) + offline breach DBs. |
| **📱 Phone Leak Checker** | Search phone numbers across Pastebin, Ghostbin, and other OSINT dork sources. |
| **🕳️ Dark Web Scanner** | Crawl `.onion` mirrors (via Tor) to search for breached data across hidden forums. |
| **📂 Offline Leak DB Support** | Use `leak_database.json` for offline demo or fallback when APIs are unavailable. |

---

## 🧱 Project Structure

```
Reconsphere/
│
├── app.py                  # Main Streamlit app — entry point
├── face_module.py          # Face upload, reverse image search, face match UI
├── reverse_search.py       # Bing-based reverse image parser
├── face_compare.py         # AI face comparison (facenet-pytorch)
├── email_leak_checker.py   # Email leak detection (HIBP + offline)
├── phone_leak_checker.py   # Phone leak OSINT via dorks + offline DB
├── dark_web_crawler.py     # Onion-site scanner (Tor proxy required)
├── utils.py                # Common helper functions
│
├── assets/
│   ├── sample_images/      # Sample images for testing
│   └── icons/              # UI icons
│
├── requirements.txt        # Python dependencies
├── DEPLOYMENT.md           # Streamlit Cloud deployment guide
├── README.md               # Project documentation (you are here)
└── leak_database.json      # Offline leak samples (for demo / testing)
```

---

## ⚙️ Installation & Setup

### 📋 Prerequisites

- **Python 3.11** — required for full compatibility with PyTorch and facenet-pytorch (3.9–3.12 may work but 3.11 is tested and recommended)
- **Git**
- *(Optional)* **Tor** — required only for the Dark Web Scanner module

---

### 🔧 Step 1 — Clone the Repository

```bash
# Clone via HTTPS
git clone https://github.com/ashish9312/Reconsphere.git

# Navigate into the project folder
cd Reconsphere
```

> **SSH alternative:**
> ```bash
> git clone git@github.com:ashish9312/Reconsphere.git
> cd Reconsphere
> ```

---

### 🐍 Step 2 — Create & Activate a Virtual Environment

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

---

### 📦 Step 3 — Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note:** `torch` and `torchvision` can be large (~1 GB). The versions in `requirements.txt` are compatible with Python 3.11. If you encounter issues, visit [pytorch.org/get-started](https://pytorch.org/get-started/locally/) to fetch a platform-specific install command.

---

### 🌐 Step 4 — (Optional) Install & Run Tor

Required **only** for the Dark Web Scanner module. The rest of the app works without Tor.

```bash
sudo apt install tor   # Debian/Ubuntu
tor &                  # Start Tor in the background
```

**Run this command**
```bash
.\venv\Scripts\python.exe train_face_calibrator.py --allow-synthetic-genuine
streamlit run app.py
```


**Windows:**
1. Download the [Tor Expert Bundle](https://www.torproject.org/download/tor/).
2. Extract and run `tor.exe` — it will start a SOCKS5 proxy on `127.0.0.1:9050`.

---

### ▶️ Step 5 — Run the App

```bash
streamlit run app.py
```

Streamlit will print a local URL (usually `http://localhost:8501`). Open it in your browser and you're ready to go!

---

## ☁️ Cloud Deployment (Streamlit Community Cloud)

Reconsphere can be deployed for free on [Streamlit Community Cloud](https://share.streamlit.io/):

1. Fork or push this repository to your GitHub account.
2. Sign in at [share.streamlit.io](https://share.streamlit.io/) with GitHub.
3. Click **Create app** → select your forked repo, branch `main`, file `app.py`.
4. In **Advanced settings**, select Python `3.11`.
5. Click **Deploy**.

> See [`DEPLOYMENT.md`](DEPLOYMENT.md) for full step-by-step instructions.

---

## 🧪 Sample Usage

| Scenario | Steps |
|----------|-------|
| **Face search** | Open *Reverse Image and Face Match* → upload a photo → view matched results. |
| **Email breach check** | Open *Email Leak Checker* → enter an email → see breach records. |
| **Phone lookup** | Open *Phone Number Leak Checker* → enter a number → view OSINT results. |
| **Offline demo** | Add sample records to `leak_database.json` and run queries without live APIs. |

---

## 🔐 Technology Stack

| Category | Stack |
|----------|-------|
| **Frontend** | Streamlit |
| **Backend** | Python 3.11 |
| **AI / Face Recognition** | facenet-pytorch, PyTorch, torchvision |
| **Image Processing** | Pillow, NumPy |
| **Web Scraping** | requests, BeautifulSoup4, lxml, fake-useragent |
| **Dark Web Access** | Tor proxy (SOCKS5) via `requests` |
| **Search** | Bing Visual Search reverse-image API workaround |
| **Offline DB** | JSON-based local breach database |

---

## 🧠 Authors & Credits

- **Developer:** Ashish — MCA Major Project
- **AI Copilot:** ChatGPT (OpenAI)
- **Powered by:** Open Source libraries & free APIs

---

## 📜 License & Disclaimer

> ⚠️ **This project is intended for academic and ethical research purposes only.**
> Unauthorized use against individuals or systems without explicit consent is illegal and unethical.
> The author does not promote or support any illegal activity.

Use responsibly. 🔒

