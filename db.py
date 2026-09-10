import sqlite3, os, csv, io

DB_DIR = os.path.join(os.path.dirname(__file__), "results")
DB_PATH = os.path.join(DB_DIR, "benchmark.db")

def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mos_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            case_id TEXT,
            provider TEXT,
            variant TEXT,
            naturalness INTEGER,
            intelligibility INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

def save_mos_rating(session_id: str, case_id: str, provider: str, variant: str, naturalness: int, intelligibility: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO mos_ratings (session_id, case_id, provider, variant, naturalness, intelligibility)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_id, case_id, provider, variant, naturalness, intelligibility))
    conn.commit()
    conn.close()

def get_all_mos_ratings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, session_id, case_id, provider, variant, naturalness, intelligibility, timestamp FROM mos_ratings ORDER BY id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def export_mos_csv_string() -> str:
    rows = get_all_mos_ratings()
    output = io.StringIO()
    fieldnames = ["id", "session_id", "case_id", "provider", "variant", "naturalness", "intelligibility", "timestamp"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return output.getvalue()

init_db()
