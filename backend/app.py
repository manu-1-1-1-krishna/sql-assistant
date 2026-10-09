"""
app.py — QueryPilot Flask application entry point.

Endpoints:
  GET  /            → serves index.html
  GET  /api/health  → application and configuration status
  GET  /api/schema  → permitted table/column metadata
  POST /api/query   → NL → SQL → execute → return results
"""

import os
import sys

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Load .env before anything else (simple manual loader — no python-dotenv dep needed)
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.isfile(_env_path):
    with open(_env_path, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _, _val = _line.partition("=")
                os.environ.setdefault(_key.strip(), _val.strip())

# Local modules — imported after env is loaded
import database as db
import gemini_client as ai

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "templates")
app = Flask(__name__, static_folder=None)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ---------------------------------------------------------------------------
# Initialise database on startup
# ---------------------------------------------------------------------------
try:
    db.init_db()
    print(f"[DB] Database ready at: {db.DB_PATH}")
except Exception as _exc:
    print(f"[DB] WARN: Could not initialise database: {_exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _error(message: str, status: int = 400) -> tuple:
    return jsonify({"success": False, "error": message}), status


def _ok(payload: dict) -> tuple:
    payload["success"] = True
    return jsonify(payload), 200


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the frontend."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/api/health", methods=["GET"])
def health():
    """Return application and configuration status."""
    api_key_set = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    db_ok = os.path.isfile(db.DB_PATH)
    schema_ok = False
    table_count = 0
    if db_ok:
        try:
            schema = db.get_schema()
            table_count = len(schema)
            schema_ok = table_count > 0
        except Exception:
            pass

    return _ok({
        "status":       "ok" if (api_key_set and db_ok and schema_ok) else "degraded",
        "api_key_set":  api_key_set,
        "model":        os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        "database_ok":  db_ok,
        "schema_ok":    schema_ok,
        "table_count":  table_count,
        "version":      "1.0.0",
    })


@app.route("/api/schema", methods=["GET"])
def schema():
    """Return permitted table and column metadata."""
    try:
        tables = db.get_schema()
        return _ok({"tables": tables})
    except Exception as exc:
        return _error(f"Failed to retrieve schema: {exc}", 500)


@app.route("/api/query", methods=["POST"])
def query():
    """
    Accept a natural-language question, generate SQL, execute it, return results.

    Request body (JSON):
      { "question": "..." }

    Response body (JSON):
      {
        "success": true,
        "question": "...",
        "sql": "...",
        "explanation": "...",
        "columns": [...],
        "rows": [...],
        "row_count": N,
        "truncated": false,
      }
    """
    body = request.get_json(silent=True) or {}
    question = (body.get("question") or "").strip()

    if not question:
        return _error("Question must not be empty.")
    if len(question) > 1000:
        return _error("Question is too long (max 1000 characters).")

    # 1. Load schema DDL for the AI prompt
    try:
        schema_ddl = db.get_schema_as_ddl()
    except Exception as exc:
        return _error(f"Could not load database schema: {exc}", 500)

    # 2. Generate SQL with Gemini
    sql = None
    try:
        sql = ai.generate_sql(question, schema_ddl)
    except RuntimeError as exc:
        # API/configuration error
        return _error(str(exc), 503)
    except ValueError as exc:
        # Model could not generate a query
        return _error(str(exc), 422)

    # 3. Validate and execute the query
    result = None
    try:
        result = db.execute_query(sql)
    except ValueError as exc:
        # Invalid SQL — attempt one AI correction
        correction_error = str(exc)
        try:
            correction_prompt = (
                f"The following SQLite query caused an error.\n"
                f"Error: {correction_error}\n"
                f"Original query:\n{sql}\n\n"
                f"Please provide a corrected SELECT query using only this schema:\n{schema_ddl}"
            )
            sql = ai.generate_sql(correction_prompt, schema_ddl)
            result = db.execute_query(sql)
        except Exception as retry_exc:
            return _error(
                f"Generated SQL was invalid and could not be corrected: {retry_exc}"
            )
    except RuntimeError as exc:
        # Execution error — attempt one AI correction
        exec_error = str(exc)
        try:
            correction_prompt = (
                f"The following SQLite query caused a runtime error.\n"
                f"Error: {exec_error}\n"
                f"Original query:\n{sql}\n\n"
                f"Please provide a corrected SELECT query using only this schema:\n{schema_ddl}"
            )
            sql = ai.generate_sql(correction_prompt, schema_ddl)
            result = db.execute_query(sql)
        except Exception as retry_exc:
            return _error(
                f"Query execution failed: {retry_exc}", 500
            )

    # 4. Generate explanation
    explanation = ai.explain_query(question, sql)

    return _ok({
        "question":    question,
        "sql":         sql,
        "explanation": explanation,
        "columns":     result["columns"],
        "rows":        result["rows"],
        "row_count":   result["row_count"],
        "truncated":   result["truncated"],
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    print(f"[APP] Starting QueryPilot on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
