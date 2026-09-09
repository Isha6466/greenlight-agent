# 🎬 Greenlight — AI Production Planning Pipeline

> Autonomous multi-agent pipeline that transforms scene descriptions into grounded location research, technical set breakdowns, and downloadable production briefs.

Built for the **Google Cloud Agentic Cinema Hackathon** (Partner Track: **Parallel**).

---

## 💡 Overview

Pre-production planning often stalls between creative vision and logistics. **Greenlight** acts as an autonomous line producer and location scout:
1. Analyzes scene tone, mood, and narrative stakes using **Gemini**.
2. Evaluates whether the scene requires real-world physical grounding, digital photogrammetry, or an indoor soundstage.
3. Automatically triggers deep web intelligence via **Parallel Task API** to scout viable locations (logistics, safety, border proximity, and permits).
4. Collaborates interactively with the filmmaker on camera, lighting, and props before locking choices.
5. Deterministically compiles a multi-page **Production Brief & Location Dossier PDF** via ReportLab.

---

## 🏗️ Architecture

```bash
User Scene Input
│
▼
┌──────────────────────────────────────┐
│  Greenlight Root Orchestrator        │ (Google ADK)
└──────────────────────────────────────┘
│
├─► Agent 1: Scene Interpreter (Gemini)
│     └─► Gating Logic: Grounding Needed? [YES / NO]
│
├─► Agent 2: Location Research (Runs ONLY if YES)
│     └─► Parallel Task API (Live schema-enforced research)
│
└─► Agent 3: Set & VFX Detailing (Gemini)
└─► Filmmaker Confirmation Loop (Location, Props, Camera, Safety)
│
▼
┌────────────────────────────────────────────────────────┐
│ Deterministic Post-Processing Pipeline                 │
│  ├─► Parallel Task API: Deep Location Dossier          │
│  │    (Seasonality, weather risks, nearest hospitals)  │
│  └─► ReportLab: Crew-Ready Multi-Page PDF Generation   │
└────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

* **Reasoning Engine:** Gemini (`gemini-3.6-flash`) via Google Agent Development Kit (ADK)
* **Agent Framework:** `google-cloud-aiplatform[agent_engines,adk]`
* **External Intelligence:** Parallel Task API (`parallel-web` SDK)
* **Deterministic Document Engine:** ReportLab (Clean PDF compilation without LLM token formatting bugs)
* **Configuration:** Python-dotenv

---

## 📁 Project Structure

```bash
agentic_cinema/
├── agent.py                 # Root orchestrator + deterministic PDF-trigger callback
├── report_generator.py      # ReportLab deterministic PDF builder
├── location_dossier.py      # Post-confirmation research via Parallel Task API
├── requirements.txt         # Core dependencies
├── .env.example             # Template for API credentials
└── sub_agents/
├── scene_interpreter/   # Agent 1: Tone, stakes, and grounding gating
├── location_research/   # Agent 2: Parallel Task API scout
└── set_design/          # Agent 3: Crew brief & confirmation loop
```

---

## 🚀 Quickstart & Local Setup


1. Clone & Set Up Environment
git clone [https://github.com/Isha6466/greenlight-agent](https://github.com/Isha6466/greenlight-agent.git)
cd greenlight-agent
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

2. Configure Credentials
Copy .env.example to .env and fill in your keys:
cp .env.example .env

GEMINI_API_KEY=your_gemini_api_key
PARALLEL_API_KEY=your_parallel_api_key


3. Launch Development UI
Run the local ADK interface:

adk web

## 🚀 Quickstart & Local Setup

### 1. Clone & Set Up Environment
```bash
git clone [https://github.com/Isha6466/greenlight-agent.git](https://github.com/Isha6466/greenlight-agent.git)
cd greenlight-agent
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt


2. Configure Credentials
Copy .env.example to .env and fill in your keys:
cp .env.example .env

GEMINI_API_KEY=your_gemini_api_key
PARALLEL_API_KEY=your_parallel_api_key

3. Launch Development UI
Run the local ADK interface:
adk web
Open http://localhost:8000 in your browser. All generated PDF briefs are deterministically exported to the local output/ directory.

📄 License
MIT License
Once you update that section and ensure `.env.example` only has placeholders, you're clear to push.