
# QueryPilot — AI SQL Query Assistant

An AI-powered SQL assistant that converts natural language questions into SQL queries, executes them against a database, and presents the results in an easy-to-understand format.

Built for the **TCS Hackathon**.

## 🚀 Project Overview

QueryPilot allows users to interact with databases using plain English instead of writing SQL manually. It uses Google Gemini AI to generate SQL queries based on the actual database schema and displays the results in a user-friendly interface.

## ✨ Features

- Natural language to SQL conversion
- AI-powered query generation using Gemini
- Database schema awareness
- SQLite query execution
- Read-only query validation
- Interactive query results table
- Sample database for demonstration
- Error handling and loading indicators
- Responsive user interface

## 🛠️ Tech Stack

- **Backend:** Python, Flask
- **Database:** SQLite
- **AI:** Google Gemini API
- **Frontend:** HTML, CSS, JavaScript
- **SDK:** Google Gen AI SDK

## 📁 Project Structure

    sql-assistant/
    ├── backend/
    │   ├── app.py
    │   ├── requirements.txt
    │   └── .env.example
    ├── .gitignore
    └── README.md

## ⚙️ Getting Started

### Prerequisites

- Python 3.10 or later
- Git
- A Google Gemini API key

### 1. Clone the Repository

    git clone https://github.com/midhunmanesh01-code/sql-assistant.git
    cd sql-assistant

### 2. Create a Virtual Environment

    cd backend
    python -m venv venv

Activate it on Windows PowerShell:

    .\venv\Scripts\Activate.ps1

### 3. Install Dependencies

    pip install -r requirements.txt

### 4. Configure Environment Variables

Create a `.env` file inside the `backend/` directory.

Add the following configuration:

    GEMINI_API_KEY=your_gemini_api_key_here
    GEMINI_MODEL=gemini-2.5-flash

Replace the placeholder with your own Gemini API key.

**Never commit your `.env` file or expose your API key publicly.**

### 5. Run the Application

    python app.py

Open the application in your browser:

http://127.0.0.1:5000

## 🔐 Security

- Store API keys in environment variables.
- Restrict SQL execution to validated, read-only queries.
- Limit the number of returned rows.
- Never expose API credentials in frontend code.
- Do not execute untrusted SQL without validation.

## 👥 Team

Developed collaboratively for the TCS Hackathon.

## 📌 Project Status

🚧 **In Development**

Features and documentation will be updated as development progresses.
