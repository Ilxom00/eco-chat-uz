import sqlite3
conn = sqlite3.connect("ecochat.db")
c = conn.cursor()
tables = [
    "employees", "branches", "topics", "questions", "question_answers",
    "employee_topic_assignments", "employee_topic_questions", "test_attempts",
    "attempt_questions", "audit_logs"
]
for table in tables:
    try:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"{table}: {c.fetchone()[0]}")
    except Exception as e:
        print(f"{table}: Error: {e}")
