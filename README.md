# QueryPilot — AI SQL Query Assistant

An AI-powered SQL assistant that converts natural-language questions into SQL queries, executes them against a real SQLite database, and presents results in a polished dark-themed dashboard.

Built for the **TCS Hackathon**.

---

## ✨ Features

| Feature | Detail |
|---|---|
| Natural language → SQL | Google Gemini generates SQL from plain English |
| Schema-aware prompts | Gemini receives the actual DDL before generating |
| Safe read-only execution | SQLite authorizer + URI read-only mode + keyword validation |
| One-shot AI correction | Invalid SQL is corrected automatically (once) |
| Real results | Only actual database rows are displayed |
| Polished dashboard | Dark-themed, responsive, hackathon-ready UI |
| Copy-to-clipboard | One-click SQL copy |
| Health endpoint | Live API key and database status in the navbar |

---

## 🛠️ Tech Stack

- **Backend:** Python 3.13, Flask 3.x, Flask-CORS
- **Database:** SQLite (built-in `sqlite3`)
- **AI:** Google Gemini via `google-genai` SDK
- **Frontend:** HTML5, CSS3, Vanilla JavaScript

---

## 📁 Project Structure

```
sql-assistant/
├── backend/
│   ├── app.py              ← Flask application (entry point)
│   ├── database.py         ← DB init, schema, safe query execution
│   ├── gemini_client.py    ← Gemini AI wrapper
│   ├── requirements.txt
│   ├── .env.example        ← Copy to .env and add your key
│   ├── school.db           ← SQLite database (auto-created, git-ignored)
│   ├── templates/
│   │   └── index.html      ← Frontend dashboard
│   └── venv/               ← Virtual environment (git-ignored)
├── .gitignore
└── README.md
```

---

## ⚙️ Getting Started

### Prerequisites

- Python 3.10 or later
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

### 1. Clone the repository

```powershell
git clone https://github.com/midhunmanesh01-code/sql-assistant.git
cd sql-assistant
```

### 2. Activate the virtual environment

```powershell
cd backend
.\\venv\\Scripts\\Activate.ps1
```

> If you see a policy error, run first:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 3. Install dependencies (if needed)

```powershell
pip install -r requirements.txt
```

### 4. Configure the API key

```powershell
Copy-Item .env.example .env
# Then open .env and replace the placeholder with your real Gemini API key
notepad .env
```

Your `.env` should contain:

```
GEMINI_API_KEY=AIza...your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### 5. Run the application

```powershell
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

---

## 🔌 API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serves the frontend |
| `GET` | `/api/health` | Returns API key and DB status |
| `GET` | `/api/schema` | Returns table/column metadata |
| `POST` | `/api/query` | Body: `{"question":"..."}` → SQL + results |

### `/api/query` response

```json
{
  "success": true,
  "question": "Show all CSE students",
  "sql": "SELECT ...",
  "explanation": "This query retrieves ...",
  "columns": ["student_id", "name", "department", "year", "email"],
  "rows": [[1, "Aarav Sharma", "CSE", 2, "aarav@college.edu"], ...],
  "row_count": 6,
  "truncated": false
}
```

---

## 🗃️ Sample Database

The database (`school.db`) is created automatically on first run with three tables:

- **students** — 15 records across CSE, ECE, IT, MECH departments
- **courses** — 10 courses with credits
- **marks** — 45+ marks records with foreign keys

Seeding is idempotent — re-running the app never duplicates records.

---

## 🔐 Security

- API keys are stored in `.env` only — never in code, logs, or responses.
- All SQL is executed through a **read-only SQLite URI connection**.
- A custom **SQLite authorizer** denies all write/DDL operations at the engine level.
- Keyword validation rejects INSERT, UPDATE, DELETE, DROP, ALTER, ATTACH, PRAGMA, etc.
- Multiple statements (`;` separator) are rejected.
- SQL comments (`--`, `/*`) are rejected.
- Results are capped at **100 rows** with a **10-second timeout**.
- Table access is restricted to the `students`, `courses`, and `marks` whitelist.
- All data is rendered via `textContent` (no `innerHTML`) to prevent XSS.

---

## 🧯 Troubleshooting

| Symptom | Fix |
|---|---|
| Navbar shows "API key missing" | Add `GEMINI_API_KEY` to `backend/.env` |
| Navbar shows "Backend unavailable" | Make sure `python app.py` is running |
| "Only SELECT statements are permitted" | The AI generated a non-SELECT — retry your question |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` inside the venv |
| PowerShell execution policy error | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |

---

## 👥 Team

Developed for the **TCS Hackathon**.

## 📌 Project Status

✅ **Working MVP** — all core features implemented and tested.
