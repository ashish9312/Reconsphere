# 🛡️ CyberIntelX: AI-Powered OSINT & Leak Detection Suite

A powerful, real-time reconnaissance tool that combines **facial recognition**, **reverse image search**, and **dark web breach analysis** — all in one web-based app built for cybersecurity enthusiasts, students, and professionals.

---

## 🚀 Features

| Module | Description |
|--------|-------------|
| **🖼️ FaceRecon** | Upload a face photo and find matching profiles across Reddit, Pinterest, Bing using reverse image search + AI-based face matching. |
| **📧 Email Leak Checker** | Enter an email and scan HaveIBeenPwned (HIBP) + offline breach DBs. |
| **📱 Phone Leak Checker** | Search phone numbers across Pastebin, Ghostbin, and other OSINT dork sources. |
| **🕳️ Dark Web Scanner** | Crawl onion mirrors (via Tor) to search for breached data across hidden forums. |
| **📂 Offline Leak DB Support** | Use `leak_database.json` for offline demo or fallback when API fails. |

---

## 🧱 Project Structure

CyberIntelX/ │ ├── app.py # Main Streamlit app (UI controller) ├── face_module.py # Face upload, reverse image search, face match ├── reverse_search.py # Bing-based reverse image parser ├── face_compare.py # AI face comparison (face_recognition) ├── email_leak_checker.py # Email leak detection (HIBP + offline) ├── phone_leak_checker.py # Phone leak OSINT via dorks + offline ├── dark_web_crawler.py # Onion-site scanner (Tor proxy required) ├── utils.py # Common helper functions │ ├── assets/ │ ├── sample_images/ │ └── icons/ │ ├── requirements.txt # Python dependencies ├── README.md # Project documentation └── leak_database.json # Offline leak samples (for demo/testing)


---

## ⚙️ Installation & Setup

### 🔧 1. Clone & Setup Environment
```bash
git clone https://github.com/yourusername/CyberIntelX.git
cd CyberIntelX
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
📦 2. Install Requirements

pip install -r requirements.txt
🌐 3. (Optional) Install & Run Tor
For dark_web_crawler.py to work, Tor must be running on port 9050.

Linux/macOS:
sudo apt install tor
tor &
Windows:

Install the Tor Expert Bundle.

Run tor.exe to start the proxy.

▶️ Running the App

streamlit run app.py
🧪 Sample Usage
Upload a random face → See similar public photos online.

Input an email or phone → Detect if leaked in known breaches.

Use Dark Web Scanner → Search hidden onion mirrors for mentions.

Offline Demo? Add emails/phones in leak_database.json.

🔐 Technology Stack
Category	Stack
Frontend	Streamlit
Backend	Python
Image Processing	face_recognition, OpenCV
Web Scraping	requests, BeautifulSoup
NLP & Analysis	regex, fallback leak DB, dork search
Dark Web Access	Tor proxy (SOCKS5) via stem, requests
Search	Bing Visual Search workaround
🧠 Authors & Credits
Built by [Your Name]
Mentor: ChatGPT (AI Copilot)
Powered by Open Source & Free APIs.

📜 License
This project is for academic and ethical research purposes only.
No illegal activity is promoted or supported.

