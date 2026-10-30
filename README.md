# AIDA — Automated Intelligent Data Agent

AIDA (Automated Intelligent Data Agent) is a full-stack, autonomous data analysis assistant. Users can upload a CSV dataset, and AIDA uses a custom **ReAct (Reasoning and Acting)** tool-calling loop to explore the schema, generate plots, perform statistical hypothesis tests, train baseline machine learning models, and write summaries of insights in plain English—all without hardcoded analysis paths.

Powered by **Groq (Llama 3.3 70B)** for lightning-fast, high-reasoning agentic execution.

---

## 📸 Architecture & Workflow

```
[ React Dashboard UI ]
         │
         ▼ (Upload CSV / Query)
[ FastAPI Backend API ]
         │
         ▼ (Start Loop)
[ ReAct Agent Engine (Llama 3.3 70B via Groq) ] ── (Executes) ──► [ Local Python Tools ]
         │                                                                │
         ◄── (Returns computed results / chart paths) ────────────────────┘
```

1. **Upload & Load**: The CSV is uploaded and loaded into Pandas memory on the backend (the raw dataset is never sent to the LLM to protect data privacy and context window size).
2. **Understand Schema**: AIDA automatically profiles the schema (columns, types, null counts) first.
3. **Plan & Execute**: Depending on the user's natural language request, the agent decides which analytical tools to invoke (plotting distribution, heatmaps, statistical tests, or machine learning model training).
4. **Self-Correction**: If a tool call or validation check fails, the backend catches the error, sends it back to the agent as feedback, and lets the model self-correct on the next turn.
5. **Stream Output**: The thought processes and tool outputs are streamed back to the React UI in real-time using Server-Sent Events (SSE).

---

## 🚀 Key Features

* **Sleek Glassmorphic UI**: A dark-theme dashboard showing configurations, interactive dataset tables, live stream progress, and collapsible execution thought traces.
* **Auto-Statistical Testing**: Automatically runs and interprets Welch's t-test, ANOVA, Pearson correlation, or Chi-Square tests based on variable types and cardinality.
* **Seaborn/Matplotlib Plotting**: Generates numerical/categorical distribution plots, bivariate charts, and correlation heatmaps, showing them in the chat and pinning them to a sidebar gallery.
* **Automated Machine Learning**: Implements a Scikit-Learn Random Forest Classifier/Regressor pipeline (handling data cleaning, scaling, and imputations) to evaluate accuracy/AUC/RMSE and output feature importances.
* **Resilient Agent Loop**: Programmatic HTTP proxy bypasses and API error-handling to ensure Llama-3.3 can recover from syntax mistakes.

---

## 🛠️ Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── agent.py         # ReAct loop and Groq SDK orchestration
│   │   ├── config.py        # Environment loader
│   │   ├── main.py          # FastAPI web server & endpoints
│   │   ├── state.py         # Global dataset & charts state variables
│   │   └── tools.py         # Pandas, SciPy, and Scikit-Learn tools
│   ├── static/charts/       # Generated visual charts (git-ignored)
│   ├── uploads/             # User uploaded CSVs (git-ignored)
│   ├── requirements.txt     # Python backend dependencies
│   └── .env                 # API Credentials (git-ignored)
├── dataset/                 # Sample credit scoring datasets
├── frontend/
│   ├── package.json         # Node.js dependencies
│   ├── index.html           # Main page setup
│   └── src/
│       ├── App.jsx          # App shell: state, upload, SSE chat orchestration
│       ├── App.css          # Design tokens (dark/light), layout, components
│       ├── api.js           # Backend client (upload w/ progress, SSE stream)
│       ├── config.js        # API base URL (override with VITE_API_BASE)
│       ├── components/      # Header, DatasetPanel, ChatPanel, ResultsPanel,
│       │                    # Markdown renderer, PlotModal, Toasts, Icon
│       └── hooks/useTheme.js
└── .gitignore               # Root gitignore rules ignoring keys and datasets
```

---

## ⚙️ Setup and Run Instructions

### 1. Prerequisite API Credentials
Create a file named `.env` in the `backend/` directory:
```bash
# backend/.env
GROQ_API_KEY=your_groq_api_key_here
# Optional: override the default model
# GROQ_MODEL=openai/gpt-oss-120b
```
*(Get a free API key from the [Groq Console](https://console.groq.com/))*

### 2. Run the Backend (FastAPI)
Navigate to the `backend/` directory and install dependencies:
```bash
cd backend
pip install -r requirements.txt
```
Start the local development server (from inside `backend/`):
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Run the Frontend (React Vite)
Open a separate terminal window, navigate to the `frontend/` folder, and install packages:
```bash
cd frontend
npm install
```
Start the Vite dev server:
```bash
npm run dev
```

Open **[http://localhost:5173](http://localhost:5173)** in your browser and upload a dataset to begin!

---
