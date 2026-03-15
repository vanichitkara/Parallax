# 🔭 Parallax — Multimodal UX Intelligence

> **One click. Infinite perspectives. Zero blind spots.**

Parallax is a next-gen **UI Navigator Agent** that uses Gemini 2.5 Flash to simultaneously test websites through the eyes of diverse user personas. From a 72-year-old retiree to a Gen Z power user, Parallax "sees" the UI, navigates autonomously, and identifies UX friction points before your users do.

---

## 🚀 Hackathon Quick Links

- **🎨 Production Dashboard**: [https://bit.ly/parallax-agent](https://bit.ly/parallax-agent)
- **🎬 Demo Video**: [Link to your video]
- **📝 Blog Post**: [Link to your blog post (optional)]
- **📖 API Documentation**: [https://parallax-backend-cidtyw74ra-uc.a.run.app/docs](https://parallax-backend-cidtyw74ra-uc.a.run.app/docs)

---

## 🎯 The Problem

97% of websites have usability issues, but QA teams all think alike. A 28-year-old engineer tests differently from a 72-year-old retiree. A native English speaker navigates differently than an ESL user. A sighted user and a screen reader user have completely different experiences.

---

## 💡 The Solution

Traditional QA is monolithic. Parallax creates **diverse AI personas** that browse your website simultaneously with unique cognitive models:

| Persona   | Age | Background                       | What They Find                                 |
| --------- | --- | -------------------------------- | ---------------------------------------------- |
| 👵 Martha | 72  | Retired teacher, iPad-only       | Invisible hamburger menus, tiny buttons        |
| 👨‍💻 Raj    | 28  | Sr. Engineer, power user         | Missing keyboard shortcuts, search issues      |
| 🇯🇵 Yuki   | 34  | Marketing manager (ESL)          | Confusing jargon, idiom misunderstandings      |
| 🦯 Sam    | 40  | Blind accountant (screen reader) | Missing alt text, broken heading structure     |
| 📱 Dev    | 16  | High school student (Gen Z)      | Boring design, slow feedback, text-heavy pages |
| 👩‍💼 Priya  | 55  | Small biz owner (mobile-first)   | Desktop confusion, tiny touch targets          |
| 🔨 Carlos | 45  | Construction worker (colorblind) | Color-only indicators, small buttons           |

---

## 🏗️ Architecture

<a href="https://ibb.co/hFcnPMV5"><img src="https://i.ibb.co/wh7b9L4H/Parallax-Architecture-Diagram.png" alt="Parallax-Architecture-Diagram" border="0"></a>

---

## 🚀 Spin-up Instructions

### Local Development

```bash
# 1. Clone and Setup
git clone https://github.com/YOUR_USERNAME/parallax.git
cd parallax
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 2. Environment (Add your GOOGLE_API_KEY)
cp .env.example .env

# 3. Start Backend
uvicorn api.main:app --reload

# 4. Start Frontend
cd frontend && npm install && npm run dev
```

### Production Deployment

The app is designed for **Google Cloud Run**.

```bash
bash cloud/deploy.sh
```

---

## 🛠️ Tech Stack

| Component       | Technology                 | Why                                               |
| --------------- | -------------------------- | ------------------------------------------------- |
| Agent Framework | **Google ADK**             | Multi-agent orchestration, required by hackathon  |
| AI Model        | **Gemini 2.0 Flash**       | Fast vision analysis, cost-effective              |
| Browser         | **Playwright**             | Headless screenshots + interactions               |
| Backend         | **FastAPI**                | Async Python, Cloud Run ready                     |
| Frontend        | **React + Vite**           | Live dashboard                                    |
| Cloud           | **Google Cloud Run**       | Serverless deployment                             |
| Storage         | **Google Cloud Firestore** | Real-time run history and report aggregation      |
| Storage         | **Google Cloud Storage**   | Persistent storage for agent-captured screenshots |

---

Built for the **Gemini Live Agent Challenge** 🚀
