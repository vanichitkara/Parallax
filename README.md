# 🔭 Parallax — AI-Powered UX Testing with Diverse Persona Agents

> **One click. 7 perspectives. Zero blind spots.**

Parallax deploys 7 AI agents — each embodying a unique user persona — to simultaneously test any website. Each agent "sees" through Gemini 2.0 Flash Vision, navigates like a real person with their specific limitations, and reports UX issues from their unique perspective.

## 🎯 The Problem

97% of websites have usability issues, but QA teams all think alike. A 28-year-old engineer tests differently than a 72-year-old retiree. A native English speaker navigates differently than an ESL user. A sighted user and a screen reader user have completely different experiences.

## 💡 The Solution

Parallax creates **7 diverse AI personas** that browse your website simultaneously:

| Persona   | Age | Background                       | What They Find                                 |
| --------- | --- | -------------------------------- | ---------------------------------------------- |
| 👵 Martha | 72  | Retired teacher, iPad-only       | Invisible hamburger menus, tiny buttons        |
| 👨‍💻 Raj    | 28  | Sr. Engineer, power user         | Missing keyboard shortcuts, search issues      |
| 🇯🇵 Yuki   | 34  | Marketing manager (ESL)          | Confusing jargon, idiom misunderstandings      |
| 🦯 Sam    | 40  | Blind accountant (screen reader) | Missing alt text, broken heading structure     |
| 📱 Dev    | 16  | High school student (Gen Z)      | Boring design, slow feedback, text-heavy pages |
| 👩‍💼 Priya  | 55  | Small biz owner (mobile-first)   | Desktop confusion, tiny touch targets          |
| 🔨 Carlos | 45  | Construction worker (colorblind) | Color-only indicators, small buttons           |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│              Parallax Dashboard              │
│     (Start test, live feed, reports)         │
└─────────────┬───────────────────────────────┘
              │
┌─────────────▼───────────────────────────────┐
│         Orchestrator Agent (ADK)             │
│    Routes tasks, collects results            │
├──────────┬──────────┬───────────┬────────────┤
│ Martha   │  Raj     │  Yuki     │  ... x7    │
│ Agent    │  Agent   │  Agent    │  Agents    │
│          │          │           │            │
│ Screenshot → Gemini Vision → Decide → Act   │
│ Each agent has its own browser instance      │
└──────────┴──────────┴───────────┴────────────┘
              │
┌─────────────▼───────────────────────────────┐
│          Analyst Agent                       │
│    Cross-persona patterns & report           │
└─────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- A [Gemini API key](https://aistudio.google.com/apikey)

### Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/parallax.git
cd parallax

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Set your API key
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### Run a Single Persona Test

```bash
# Test with Martha (72-year-old, low tech proficiency)
python run_navigator.py --persona martha --url "https://en.wikipedia.org" --task "Find information about climate change"

# Test with Raj (28-year-old power user)
python run_navigator.py --persona raj --url "https://en.wikipedia.org" --task "Find information about climate change"

# Test with Sam (screen reader user)
python run_navigator.py --persona sam --url "https://en.wikipedia.org" --task "Find information about climate change"
```

### Run Multi-Persona Comparison

```bash
# Test 3 personas and compare results
python run_multi_test.py --personas martha,raj,dev --url "https://en.wikipedia.org" --task "Find information about climate change"
```

### Run with ADK Web Interface

```bash
# Start ADK's built-in web UI
adk web --port 8000
# Open http://localhost:8000 and select "parallax_agent"
```

## 📁 Project Structure

```
parallax/
├── parallax_agent/          # ADK Agent (entry point for `adk web`)
│   ├── __init__.py
│   └── agent.py             # Root agent with browser tools
├── personas/                # Persona definitions
│   ├── definitions.py       # 7 persona profiles with cognitive models
│   └── cognitive.py         # Frustration/state tracking
├── tools/                   # Browser interaction tools
│   └── browser.py           # Playwright wrapper (screenshot, click, type, scroll)
├── models/                  # Data models
│   ├── journey.py           # Step-by-step journey tracking
│   ├── finding.py           # UX issue findings
│   └── report.py            # Aggregated report model
├── run_navigator.py         # Single persona test runner
├── run_multi_test.py        # Multi-persona comparison runner
├── requirements.txt
├── .env.example
└── README.md
```

## 🛠️ Tech Stack

| Component       | Technology           | Why                                              |
| --------------- | -------------------- | ------------------------------------------------ |
| Agent Framework | **Google ADK**       | Multi-agent orchestration, required by hackathon |
| AI Model        | **Gemini 2.0 Flash** | Fast vision analysis, cost-effective             |
| Browser         | **Playwright**       | Headless screenshots + interactions              |
| Backend         | **FastAPI**          | Async Python, Cloud Run ready                    |
| Frontend        | **React + Vite**     | Live dashboard                                   |
| Cloud           | **Google Cloud Run** | Serverless deployment                            |

## 📋 Hackathon Category

**UI Navigator** — Visual UI Understanding & Interaction

Parallax uses Gemini's multimodal capabilities to interpret screenshots and perform actions based on diverse user personas, without relying on DOM access or CSS selectors.

## 📄 License

MIT

---

Built for the [Gemini Live Agent Challenge](https://geminiliveagentchallenge.devpost.com/) 🚀
