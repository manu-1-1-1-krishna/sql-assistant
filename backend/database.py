"""
database.py — SQLite database initialization and safe query execution.

Provides:
  - init_db()      : Creates tables and seeds sample data (idempotent).
  - get_schema()   : Returns permitted table/column metadata.
  - execute_query(): Executes a validated, read-only SELECT query safely.
"""

import sqlite3
import os
import re
import threading

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "school.db")

# ---------------------------------------------------------------------------
# Allowed tables (whitelist for authorizer)
# ---------------------------------------------------------------------------
ALLOWED_TABLES = {"students", "courses", "marks"}

# Query timeout in seconds
QUERY_TIMEOUT  = 10
# Maximum rows returned
MAX_ROWS       = 100

# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    student_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    department  TEXT    NOT NULL,
    year        INTEGER NOT NULL CHECK(year BETWEEN 1 AND 4),
    email       TEXT    UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS courses (
    course_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    course_name TEXT    NOT NULL,
    department  TEXT    NOT NULL,
    credits     INTEGER NOT NULL CHECK(credits BETWEEN 1 AND 6)
);

CREATE TABLE IF NOT EXISTS marks (
    mark_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id),
    course_id  INTEGER NOT NULL REFERENCES courses(course_id),
    marks      INTEGER NOT NULL CHECK(marks BETWEEN 0 AND 100),
    semester   TEXT    NOT NULL,
    UNIQUE(student_id, course_id, semester)
);
"""

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
STUDENTS = [
    ("Aarav Sharma",    "CSE", 2, "aarav@college.edu"),
    ("Priya Nair",      "CSE", 3, "priya@college.edu"),
    ("Rohit Verma",     "ECE", 1, "rohit@college.edu"),
    ("Sneha Pillai",    "CSE", 2, "sneha@college.edu"),
    ("Vikram Singh",    "MECH",4, "vikram@college.edu"),
    ("Divya Menon",     "CSE", 3, "divya@college.edu"),
    ("Arjun Das",       "ECE", 2, "arjun@college.edu"),
    ("Kavya Reddy",     "CSE", 1, "kavya@college.edu"),
    ("Ananya Iyer",     "IT",  3, "ananya@college.edu"),
    ("Siddharth Kumar", "MECH",2, "siddharth@college.edu"),
    ("Meera Joshi",     "IT",  4, "meera@college.edu"),
    ("Rahul Bose",      "CSE", 4, "rahul@college.edu"),
    ("Pooja Gupta",     "ECE", 3, "pooja@college.edu"),
    ("Nikhil Tiwari",   "CSE", 2, "nikhil@college.edu"),
    ("Swathi Rao",      "IT",  1, "swathi@college.edu"),
]

COURSES = [
    ("Data Structures",        "CSE",  4),
    ("Database Management",    "CSE",  4),
    ("Operating Systems",      "CSE",  3),
    ("Circuit Theory",         "ECE",  4),
    ("Digital Electronics",    "ECE",  3),
    ("Thermodynamics",         "MECH", 4),
    ("Python Programming",     "IT",   3),
    ("Web Technologies",       "IT",   3),
    ("Machine Learning",       "CSE",  4),
    ("Computer Networks",      "CSE",  3),
]

# (student_index, course_index, marks, semester)
MARKS = [
    # Aarav — CSE yr2
    (1,  1, 88, "2024-S1"), (1,  2, 75, "2024-S1"), (1,  3, 92, "2024-S2"),
    (1,  9, 84, "2024-S2"), (1, 10, 79, "2024-S2"),
    # Priya — CSE yr3
    (2,  1, 95, "2024-S1"), (2,  2, 91, "2024-S1"), (2,  3, 88, "2024-S2"),
    (2,  9, 97, "2024-S2"), (2, 10, 93, "2024-S2"),
    # Rohit — ECE yr1
    (3,  4, 72, "2024-S1"), (3,  5, 68, "2024-S1"),
    # Sneha — CSE yr2
    (4,  1, 80, "2024-S1"), (4,  2, 85, "2024-S1"), (4,  3, 78, "2024-S2"),
    (4,  9, 90, "2024-S2"), (4, 10, 82, "2024-S2"),
    # Vikram — MECH yr4
    (5,  6, 65, "2024-S1"), (5,  6, 70, "2024-S2"),
    # Divya — CSE yr3
    (6,  1, 93, "2024-S1"), (6,  2, 89, "2024-S1"), (6,  9, 96, "2024-S2"),
    (6, 10, 87, "2024-S2"),
    # Arjun — ECE yr2
    (7,  4, 76, "2024-S1"), (7,  5, 82, "2024-S1"),
    # Kavya — CSE yr1
    (8,  1, 74, "2024-S1"), (8,  3, 69, "2024-S1"),
    # Ananya — IT yr3
    (9,  7, 88, "2024-S1"), (9,  8, 91, "2024-S1"),
    # Siddharth — MECH yr2
    (10, 6, 58, "2024-S1"), (10, 6, 63, "2024-S2"),
    # Meera — IT yr4
    (11, 7, 94, "2024-S1"), (11, 8, 89, "2024-S1"),
    # Rahul — CSE yr4
    (12, 1, 91, "2024-S1"), (12, 2, 94, "2024-S1"), (12, 9, 98, "2024-S2"),
    (12, 10, 95, "2024-S2"),
    # Pooja — ECE yr3
    (13, 4, 85, "2024-S1"), (13, 5, 79, "2024-S1"),
    # Nikhil — CSE yr2
    (14, 1, 67, "2024-S1"), (14, 2, 71, "2024-S1"), (14, 3, 64, "2024-S2"),
    # Swathi — IT yr1
    (15, 7, 82, "2024-S1"), (15, 8, 77, "2024-S1"),
]


def init_db() -> None:
    """Create tables and seed data idempotently."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        conn.executescript(SCHEMA_SQL)

        # Check if students table is empty before seeding
        cur = conn.execute("SELECT COUNT(*) FROM students")
        if cur.fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO students (name, department, year, email) VALUES (?,?,?,?)",
                STUDENTS,
            )
            conn.executemany(
                "INSERT INTO courses (course_name, department, credits) VALUES (?,?,?)",
                COURSES,
            )
            conn.executemany(
                "INSERT INTO marks (student_id, course_id, marks, semester) VALUES (?,?,?,?)",
                MARKS,
            )
            conn.commit()
            print("[DB] Sample data seeded successfully.")
        else:
            print("[DB] Database already populated; skipping seed.")
    finally:
        conn.close()


def get_schema() -> dict:
    """Return permitted table and column metadata."""
    conn = sqlite3.connect(DB_PATH)
    schema = {}
    try:
        for table in ALLOWED_TABLES:
            cur = conn.execute(f"PRAGMA table_info({table})")
            columns = [
                {
                    "name":     row[1],
                    "type":     row[2],
                    "notnull":  bool(row[3]),
                    "pk":       bool(row[5]),
                }
                for row in cur.fetchall()
            ]
            schema[table] = columns
    finally:
        conn.close()
    return schema


def get_schema_as_ddl() -> str:
    """Return schema as a DDL string for use in AI prompts."""
    conn = sqlite3.connect(DB_PATH)
    lines = []
    try:
        for table in sorted(ALLOWED_TABLES):
            cur = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            row = cur.fetchone()
            if row:
                lines.append(row[0] + ";")
    finally:
        conn.close()
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Query validation
# ---------------------------------------------------------------------------
# Forbidden patterns — checked in addition to the SQLite authorizer.
_FORBIDDEN_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|ATTACH|DETACH"
    r"|PRAGMA|VACUUM|REINDEX|ANALYZE|GRANT|REVOKE|TRUNCATE)\b",
    re.IGNORECASE,
)


def _validate_query(sql: str) -> str:
    """
    Validate the SQL before execution.
    Returns the stripped, validated query or raises ValueError.
    """
    sql = sql.strip().rstrip(";")

    # Reject multiple statements
    if ";" in sql:
        raise ValueError("Multiple SQL statements are not permitted.")

    # Must start with SELECT
    if not re.match(r"^\s*SELECT\b", sql, re.IGNORECASE):
        raise ValueError("Only SELECT statements are permitted.")

    # Reject forbidden keywords
    if _FORBIDDEN_PATTERNS.search(sql):
        raise ValueError("Query contains a disallowed SQL keyword.")

    # Reject comment sequences that could be used to bypass checks
    if "--" in sql or "/*" in sql:
        raise ValueError("SQL comments are not permitted in queries.")

    return sql


def _make_readonly_connection() -> sqlite3.Connection:
    """
    Open a read-only URI connection and install an authorizer that
    blocks all writes, DDL, and access to tables outside the whitelist.
    """
    uri = f"file:{DB_PATH}?mode=ro"
    # check_same_thread=False is required because the connection is created
    # in a worker thread spawned by execute_query().
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)

    # SQLITE_FUNCTION action code is 31 (not exposed as a named constant in Python's sqlite3)
    SQLITE_FUNCTION = 31
    # SQLITE_RECURSIVE is 33 — needed for CTEs (WITH ... AS ...)
    SQLITE_RECURSIVE = 33

    def authorizer(action_code, arg1, arg2, db_name, trigger_name):
        # Always allow: read a column, SELECT statement, function calls, recursive CTEs
        if action_code == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK

        if action_code == sqlite3.SQLITE_READ:
            # arg1 = table name; block access to tables outside the whitelist
            if arg1 and arg1.lower() not in ALLOWED_TABLES:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        if action_code in (SQLITE_FUNCTION, SQLITE_RECURSIVE):
            # Allow all SQL functions (COUNT, AVG, SUM, MAX, MIN, strftime, …)
            return sqlite3.SQLITE_OK

        # Deny all write / DDL / ATTACH / PRAGMA / trigger operations
        return sqlite3.SQLITE_DENY

    conn.set_authorizer(authorizer)
    return conn


def execute_query(sql: str) -> dict:
    """
    Validate and execute a SELECT query safely.

    Returns:
        {
          "columns": [...],
          "rows": [...],
          "row_count": int,
          "truncated": bool,
        }

    Raises ValueError for invalid queries, RuntimeError for execution errors.
    """
    # 1. Validate
    clean_sql = _validate_query(sql)

    # 2. Execute with timeout via threading
    result_container: dict = {}
    error_container:  dict = {}

    def _run():
        conn = None
        try:
            conn = _make_readonly_connection()
            # Note: busy_timeout PRAGMA is not needed here because:
            # 1. The connection is read-only, so no write locks.
            # 2. The thread.join(QUERY_TIMEOUT) enforces the wall-clock limit.
            cur = conn.execute(clean_sql)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows    = cur.fetchmany(MAX_ROWS + 1)
            truncated = len(rows) > MAX_ROWS
            rows = rows[:MAX_ROWS]
            result_container["columns"]   = columns
            result_container["rows"]      = [list(r) for r in rows]
            result_container["row_count"] = len(rows)
            result_container["truncated"] = truncated
        except sqlite3.OperationalError as exc:
            error_container["error"] = str(exc)
        except sqlite3.DatabaseError as exc:
            error_container["error"] = f"Database error: {exc}"
        finally:
            if conn:
                conn.close()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=QUERY_TIMEOUT)

    if thread.is_alive():
        raise RuntimeError("Query execution timed out.")

    if error_container:
        raise RuntimeError(error_container["error"])

    return result_container
