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
            medication_correct INTEGER,
            strength_correct INTEGER,
            dosage_correct INTEGER,
            duration_correct INTEGER,
            date_correct INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blind_sessions (
            session_id TEXT PRIMARY KEY,
            case_id TEXT,
            raw_text TEXT,
            provider_a TEXT,
            variant_a TEXT,
            audio_id_a TEXT,
            provider_b TEXT,
            variant_b TEXT,
            audio_id_b TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    # Migration check for columns if table already exists
    cursor.execute("PRAGMA table_info(mos_ratings)")
    existing_cols = [r["name"] for r in cursor.fetchall()]
    for col in ["medication_correct", "strength_correct", "dosage_correct", "duration_correct", "date_correct"]:
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE mos_ratings ADD COLUMN {col} INTEGER")
            conn.commit()

    conn.close()

def save_blind_session(session_id: str, case_id: str, raw_text: str,
                       provider_a: str, variant_a: str, audio_id_a: str,
                       provider_b: str, variant_b: str, audio_id_b: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO blind_sessions (
            session_id, case_id, raw_text, provider_a, variant_a, audio_id_a,
            provider_b, variant_b, audio_id_b
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (session_id, case_id, raw_text, provider_a, variant_a, audio_id_a, provider_b, variant_b, audio_id_b))
    conn.commit()
    conn.close()

def get_blind_session(session_id: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blind_sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    r = dict(row)
    return {
        "case_id": r["case_id"],
        "raw_text": r["raw_text"],
        "A": {"provider": r["provider_a"], "variant": r["variant_a"], "audio_id": r["audio_id_a"]},
        "B": {"provider": r["provider_b"], "variant": r["variant_b"], "audio_id": r["audio_id_b"]}
    }

def save_mos_rating(session_id: str, case_id: str, provider: str, variant: str, naturalness: int, intelligibility: int,
                    medication_correct: bool = None, strength_correct: bool = None, dosage_correct: bool = None,
                    duration_correct: bool = None, date_correct: bool = None):
    conn = get_connection()
    cursor = conn.cursor()
    
    def to_int_or_none(val):
        if val is None: return None
        return 1 if bool(val) else 0

    cursor.execute("""
        INSERT INTO mos_ratings (
            session_id, case_id, provider, variant, naturalness, intelligibility,
            medication_correct, strength_correct, dosage_correct, duration_correct, date_correct
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id, case_id, provider, variant, naturalness, intelligibility,
        to_int_or_none(medication_correct), to_int_or_none(strength_correct),
        to_int_or_none(dosage_correct), to_int_or_none(duration_correct),
        to_int_or_none(date_correct)
    ))
    conn.commit()
    conn.close()

def get_all_mos_ratings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, session_id, case_id, provider, variant, naturalness, intelligibility,
               medication_correct, strength_correct, dosage_correct, duration_correct, date_correct, timestamp
        FROM mos_ratings ORDER BY id DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def export_mos_csv_string() -> str:
    rows = get_all_mos_ratings()
    output = io.StringIO()
    fieldnames = [
        "id", "session_id", "case_id", "provider", "variant", "naturalness", "intelligibility",
        "medication_correct", "strength_correct", "dosage_correct", "duration_correct", "date_correct", "timestamp"
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return output.getvalue()

init_db()
