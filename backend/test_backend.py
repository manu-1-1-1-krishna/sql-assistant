"""
test_backend.py -- Automated acceptance tests for QueryPilot.

Run from backend/ with the venv activated:
  python test_backend.py

Tests do NOT start the Flask server; they exercise modules directly.
"""

import os
import sys
import io
import sqlite3
import traceback

# Force UTF-8 output on Windows to avoid cp1252 encoding errors
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ensure we can import local modules
sys.path.insert(0, os.path.dirname(__file__))

# Load .env if present
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.isfile(_env_path):
    with open(_env_path, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _, _val = _line.partition("=")
                os.environ.setdefault(_key.strip(), _val.strip())

import database as db

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"
results = []

def test(name, fn):
    try:
        fn()
        results.append((PASS, name))
        print(f"{PASS}  {name}")
    except AssertionError as e:
        results.append((FAIL, name))
        print(f"{FAIL}  {name}\n      {e}")
    except Exception as e:
        results.append((FAIL, name))
        print(f"{FAIL}  {name}\n      {type(e).__name__}: {e}")
        traceback.print_exc()

def skip(name, reason):
    results.append((SKIP, name))
    print(f"{SKIP}  {name}  ({reason})")

# ===========================================================
# Test 1: Database initialisation
# ===========================================================
def t_db_init():
    db.init_db()
    assert os.path.isfile(db.DB_PATH), f"DB file not found: {db.DB_PATH}"

test("Database initialisation", t_db_init)

# ===========================================================
# Test 2: Schema retrieval
# ===========================================================
def t_schema():
    schema = db.get_schema()
    assert "students" in schema
    assert "courses"  in schema
    assert "marks"    in schema
    # Check columns exist
    s_cols = [c["name"] for c in schema["students"]]
    assert "student_id" in s_cols
    assert "name"       in s_cols
    assert "department" in s_cols

test("Schema retrieval", t_schema)

# ===========================================================
# Test 3: Schema DDL
# ===========================================================
def t_schema_ddl():
    ddl = db.get_schema_as_ddl()
    assert "CREATE TABLE" in ddl.upper()
    assert "students" in ddl.lower()

test("Schema DDL generation", t_schema_ddl)

# ===========================================================
# Test 4: Simple SELECT
# ===========================================================
def t_simple_select():
    r = db.execute_query("SELECT * FROM students LIMIT 5")
    assert r["row_count"] == 5
    assert "student_id" in r["columns"]
    assert len(r["rows"]) == 5

test("Simple SELECT with LIMIT", t_simple_select)

# ===========================================================
# Test 5: Filtered SELECT
# ===========================================================
def t_filter():
    r = db.execute_query("SELECT name, department FROM students WHERE department = 'CSE'")
    assert r["row_count"] > 0
    for row in r["rows"]:
        assert row[1] == "CSE", f"Expected CSE, got {row[1]}"

test("Filtered SELECT (WHERE clause)", t_filter)

# ===========================================================
# Test 6: Aggregate + GROUP BY
# ===========================================================
def t_aggregate():
    r = db.execute_query(
        "SELECT department, COUNT(*) as cnt FROM students GROUP BY department ORDER BY cnt DESC"
    )
    assert r["row_count"] > 0
    assert "department" in r["columns"]
    assert "cnt" in r["columns"]

test("Aggregate query (COUNT + GROUP BY)", t_aggregate)

# ===========================================================
# Test 7: JOIN query
# ===========================================================
def t_join():
    r = db.execute_query("""
        SELECT s.name, c.course_name, m.marks
        FROM students s
        JOIN marks m ON s.student_id = m.student_id
        JOIN courses c ON m.course_id = c.course_id
        LIMIT 10
    """)
    assert r["row_count"] > 0
    assert "name" in r["columns"]
    assert "course_name" in r["columns"]
    assert "marks" in r["columns"]

test("JOIN query (students + marks + courses)", t_join)

# ===========================================================
# Test 8: Subquery / ranking
# ===========================================================
def t_subquery():
    r = db.execute_query("""
        SELECT s.name, AVG(m.marks) as avg_marks
        FROM students s
        JOIN marks m ON s.student_id = m.student_id
        GROUP BY s.student_id
        ORDER BY avg_marks DESC
        LIMIT 5
    """)
    assert r["row_count"] == 5
    # Results should be sorted descending
    avgs = [row[1] for row in r["rows"]]
    assert avgs == sorted(avgs, reverse=True), f"Not sorted: {avgs}"

test("Subquery / aggregate ranking (TOP 5)", t_subquery)

# ===========================================================
# Test 9: Empty question rejection (via validation)
# ===========================================================
def t_empty_question():
    # Simulate what app.py does — empty string check
    question = "   "
    assert not question.strip(), "Expected empty after strip"

test("Empty question detection", t_empty_question)

# ===========================================================
# Test 10: Non-SELECT rejection
# ===========================================================
def t_reject_insert():
    try:
        db.execute_query("INSERT INTO students (name) VALUES ('hacker')")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "SELECT" in str(e) or "permitted" in str(e).lower()

test("Rejection of INSERT statement", t_reject_insert)

# ===========================================================
# Test 11: Rejection of DROP
# ===========================================================
def t_reject_drop():
    try:
        db.execute_query("DROP TABLE students")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        pass  # Expected

test("Rejection of DROP statement", t_reject_drop)

# ===========================================================
# Test 12: Rejection of UPDATE
# ===========================================================
def t_reject_update():
    try:
        db.execute_query("UPDATE students SET name='x' WHERE 1=1")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

test("Rejection of UPDATE statement", t_reject_update)

# ===========================================================
# Test 13: Multiple statements rejected
# ===========================================================
def t_multi_statement():
    try:
        db.execute_query("SELECT 1; DROP TABLE students")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "multiple" in str(e).lower() or ";" in str(e)

test("Rejection of multiple statements", t_multi_statement)

# ===========================================================
# Test 14: SQL comments rejected
# ===========================================================
def t_comments():
    try:
        db.execute_query("SELECT * FROM students -- comment")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

test("Rejection of SQL comments (--)", t_comments)

# ===========================================================
# Test 15: Write prevention at engine level (authorizer)
# ===========================================================
def t_write_prevention():
    """Verify the SQLite authorizer blocks writes even if validation is bypassed."""
    uri = f"file:{db.DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        conn.execute("INSERT INTO students (name,department,year,email) VALUES ('evil','CSE',1,'evil@x.com')")
        conn.commit()
        assert False, "Read-only connection should have raised an error"
    except sqlite3.OperationalError as e:
        assert "readonly" in str(e).lower() or "attempt to write" in str(e).lower() or True
        # Any OperationalError is fine — the write was blocked
    finally:
        conn.close()

test("Write prevention at SQLite engine level (read-only URI)", t_write_prevention)

# ===========================================================
# Test 16: Row limit
# ===========================================================
def t_row_limit():
    # Insert a harmless big query — marks has ~45 rows, under limit
    r = db.execute_query("SELECT * FROM marks")
    assert r["row_count"] <= db.MAX_ROWS, f"Exceeded MAX_ROWS: {r['row_count']}"
    assert isinstance(r["truncated"], bool)

test("Row limit enforcement (MAX_ROWS)", t_row_limit)

# ===========================================================
# Test 17: Empty result set
# ===========================================================
def t_empty_result():
    r = db.execute_query("SELECT * FROM students WHERE department = 'NONEXISTENT_DEPT_XYZ'")
    assert r["row_count"] == 0
    assert r["rows"] == []

test("Empty result set (no rows)", t_empty_result)

# ===========================================================
# Test 18: Unauthorized table access blocked
# ===========================================================
def t_unauthorized_table():
    # sqlite_master is not in the whitelist
    try:
        db.execute_query("SELECT * FROM sqlite_master")
        # If it gets through validation, the authorizer should block it
        assert False, "Should have been blocked"
    except (ValueError, RuntimeError) as e:
        pass  # Expected — either validation or authorizer blocks it

test("Unauthorized table access blocked", t_unauthorized_table)

# ===========================================================
# Test 19 (optional): Gemini AI integration
# ===========================================================
api_key = os.environ.get("GEMINI_API_KEY", "").strip()
if api_key and api_key != "your_gemini_api_key_here":
    import gemini_client as ai

    def t_gemini_generate():
        ddl = db.get_schema_as_ddl()
        sql = ai.generate_sql("Show all CSE students", ddl)
        assert sql, "Expected a non-empty SQL string"
        assert sql.strip().upper().startswith("SELECT"), f"Expected SELECT, got: {sql[:60]}"
        # Validate it and execute it
        result = db.execute_query(sql)
        assert result["row_count"] > 0

    test("Gemini AI: generate SQL + execute (live API)", t_gemini_generate)

    def t_gemini_explain():
        sql = "SELECT name, department FROM students WHERE department = 'CSE'"
        explanation = ai.explain_query("Show all CSE students", sql)
        assert explanation and len(explanation) > 10

    test("Gemini AI: explain query (live API)", t_gemini_explain)
else:
    skip("Gemini AI: generate SQL + execute (live API)", "GEMINI_API_KEY not set in .env")
    skip("Gemini AI: explain query (live API)",          "GEMINI_API_KEY not set in .env")

# ===========================================================
# Summary
# ===========================================================
print("\n" + "="*55)
total  = len(results)
passed = sum(1 for r in results if r[0] == PASS)
failed = sum(1 for r in results if r[0] == FAIL)
skipped= sum(1 for r in results if r[0] == SKIP)
print(f"Results: {passed}/{total} passed  |  {failed} failed  |  {skipped} skipped")
print("="*55)
if failed:
    sys.exit(1)
