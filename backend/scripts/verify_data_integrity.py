"""
eco-chat.uz — Data Integrity Verification Script
=================================================
Checks database consistency across all critical tables.

Usage:
    python verify_data_integrity.py
    python verify_data_integrity.py --json
    python verify_data_integrity.py --table employees
    python verify_data_integrity.py --json --table attempts

Exit codes:
    0 — all checks PASS (or only WARNings)
    1 — at least one check FAILed
"""

import asyncio
import os
import sys
import json
import argparse
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPECTED_ANSWERS_PER_QUESTION = 4
EXPECTED_QUESTIONS_PER_ASSIGNMENT = 15

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_WARN = "WARN"
STATUS_SKIP = "SKIP"

# Colour codes (suppressed when not a TTY)
_USE_COLOUR = sys.stdout.isatty()

COLOURS = {
    STATUS_PASS: "\033[32m",   # green
    STATUS_FAIL: "\033[31m",   # red
    STATUS_WARN: "\033[33m",   # yellow
    STATUS_SKIP: "\033[36m",   # cyan
    "RESET":     "\033[0m",
    "BOLD":      "\033[1m",
}


def _colour(status: str, text_: str) -> str:
    if not _USE_COLOUR:
        return text_
    code = COLOURS.get(status, "")
    reset = COLOURS["RESET"]
    return f"{code}{text_}{reset}"


# ---------------------------------------------------------------------------
# Result helper
# ---------------------------------------------------------------------------

def make_result(
    check_id: str,
    status: str,
    message: str,
    detail: Optional[Any] = None,
) -> Dict[str, Any]:
    return {
        "check_id": check_id,
        "status": status,
        "message": message,
        "detail": detail,
    }


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _get_database_url() -> str:
    """
    Read DATABASE_URL from the environment.  Translate sync drivers to their
    async equivalents so SQLAlchemy's async engine can be used.

    Supported translations:
        postgresql://  ->  postgresql+asyncpg://
        postgres://    ->  postgresql+asyncpg://
        sqlite:///     ->  sqlite+aiosqlite:///
    """
    url = os.getenv("DATABASE_URL", "")
    if not url:
        # Fall back to a local SQLite file relative to this script
        db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "eco_chat_dev.db"
        )
        url = f"sqlite+aiosqlite:///{os.path.normpath(db_path)}"
        print(
            f"WARNING: DATABASE_URL not set — using local SQLite: {url}",
            file=sys.stderr,
        )
        return url

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("sqlite:///"):
        url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    # already async variants fall through unchanged

    return url


def _is_sqlite(url: str) -> bool:
    return "sqlite" in url.lower()


async def _table_exists(session: AsyncSession, table: str, sqlite: bool) -> bool:
    if sqlite:
        q = text(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=:t"
        )
    else:
        q = text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=:t"
        )
    result = await session.execute(q, {"t": table})
    return (result.scalar() or 0) > 0


async def _safe_count(
    session: AsyncSession, table: str, sqlite: bool
) -> Optional[int]:
    """Return row count or None if the table does not exist."""
    if not await _table_exists(session, table, sqlite):
        return None
    result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
    return result.scalar()


# ---------------------------------------------------------------------------
# Check 1 — Orphan employees
# ---------------------------------------------------------------------------

async def check_orphan_employees(
    session: AsyncSession, sqlite: bool
) -> Dict[str, Any]:
    """Employees whose branch_id points to a non-existent branch."""
    check_id = "orphan_employees"
    try:
        for tbl in ("employees", "branches"):
            if not await _table_exists(session, tbl, sqlite):
                return make_result(
                    check_id, STATUS_WARN,
                    f"Table '{tbl}' does not exist — skipping",
                )

        q = text(
            """
            SELECT e.id, e.full_name, e.branch_id
            FROM   employees e
            LEFT   JOIN branches b ON b.id = e.branch_id
            WHERE  e.branch_id IS NOT NULL
              AND  b.id IS NULL
            """
        )
        rows = (await session.execute(q)).fetchall()
        if not rows:
            return make_result(check_id, STATUS_PASS, "Orphan employees: 0 found")
        ids = [str(r[0]) for r in rows]
        return make_result(
            check_id, STATUS_FAIL,
            f"Orphan employees: {len(rows)} found (IDs: {', '.join(ids)})",
            {"count": len(rows), "ids": ids},
        )
    except Exception as exc:
        return make_result(check_id, STATUS_FAIL, f"Check error: {exc}")


# ---------------------------------------------------------------------------
# Check 2 — Orphan attempts
# ---------------------------------------------------------------------------

async def check_orphan_attempts(
    session: AsyncSession, sqlite: bool
) -> Dict[str, Any]:
    """test_attempts referencing a missing employee or topic."""
    check_id = "orphan_attempts"
    try:
        for tbl in ("test_attempts", "employees", "topics"):
            if not await _table_exists(session, tbl, sqlite):
                return make_result(
                    check_id, STATUS_WARN,
                    f"Table '{tbl}' does not exist — skipping",
                )

        q = text(
            """
            SELECT ta.id, ta.employee_id, ta.topic_id
            FROM   test_attempts ta
            LEFT   JOIN employees e ON e.id = ta.employee_id
            LEFT   JOIN topics    t ON t.id = ta.topic_id
            WHERE  e.id IS NULL OR t.id IS NULL
            """
        )
        rows = (await session.execute(q)).fetchall()
        if not rows:
            return make_result(check_id, STATUS_PASS, "Orphan attempts: 0 found")
        ids = [str(r[0]) for r in rows]
        return make_result(
            check_id, STATUS_FAIL,
            f"Orphan attempts: {len(rows)} found (IDs: {', '.join(ids)})",
            {"count": len(rows), "ids": ids},
        )
    except Exception as exc:
        return make_result(check_id, STATUS_FAIL, f"Check error: {exc}")


# ---------------------------------------------------------------------------
# Check 3 — Assignment question count != 15
# ---------------------------------------------------------------------------

async def check_assignment_question_counts(
    session: AsyncSession, sqlite: bool
) -> Dict[str, Any]:
    """Every assignment must have exactly 15 questions."""
    check_id = "assignment_question_counts"
    try:
        for tbl in ("employee_topic_assignments", "employee_topic_questions"):
            if not await _table_exists(session, tbl, sqlite):
                return make_result(
                    check_id, STATUS_WARN,
                    f"Table '{tbl}' does not exist — skipping",
                )

        q = text(
            f"""
            SELECT a.id, COUNT(q.id) AS qcount
            FROM   employee_topic_assignments a
            LEFT   JOIN employee_topic_questions q ON q.assignment_id = a.id
            GROUP  BY a.id
            HAVING COUNT(q.id) != {EXPECTED_QUESTIONS_PER_ASSIGNMENT}
            """
        )
        rows = (await session.execute(q)).fetchall()
        if not rows:
            return make_result(
                check_id, STATUS_PASS,
                f"Assignment question counts: all assignments have "
                f"{EXPECTED_QUESTIONS_PER_ASSIGNMENT} questions",
            )
        bad = [{"assignment_id": str(r[0]), "count": r[1]} for r in rows]
        ids = [str(r[0]) for r in rows]
        return make_result(
            check_id, STATUS_FAIL,
            f"Assignment question counts: {len(rows)} assignment(s) with wrong "
            f"count (IDs: {', '.join(ids)})",
            bad,
        )
    except Exception as exc:
        return make_result(check_id, STATUS_FAIL, f"Check error: {exc}")


# ---------------------------------------------------------------------------
# Check 4 — Attempt2 question set must equal Attempt1
# ---------------------------------------------------------------------------

async def check_attempt2_question_set(
    session: AsyncSession, sqlite: bool
) -> Dict[str, Any]:
    """
    For every assignment that has both attempt 1 and attempt 2, the set of
    question IDs must be identical.
    """
    check_id = "attempt2_question_set"
    try:
        for tbl in ("test_attempts", "attempt_questions"):
            if not await _table_exists(session, tbl, sqlite):
                return make_result(
                    check_id, STATUS_WARN,
                    f"Table '{tbl}' does not exist — skipping",
                )

        q = text(
            """
            SELECT ta.assignment_id,
                   ta.attempt_number,
                   aq.question_id
            FROM   test_attempts     ta
            JOIN   attempt_questions aq ON aq.attempt_id = ta.id
            WHERE  ta.attempt_number IN (1, 2)
            ORDER  BY ta.assignment_id, ta.attempt_number, aq.question_id
            """
        )
        rows = (await session.execute(q)).fetchall()

        # Group by assignment_id -> {attempt_number: set(question_ids)}
        grouped: Dict[Any, Dict[int, set]] = defaultdict(
            lambda: {1: set(), 2: set()}
        )
        for assignment_id, attempt_num, question_id in rows:
            grouped[assignment_id][attempt_num].add(question_id)

        mismatches = []
        for asgn_id, sets in grouped.items():
            if 1 in sets and 2 in sets and sets[1] != sets[2]:
                only_in_1 = sorted(str(x) for x in sets[1] - sets[2])
                only_in_2 = sorted(str(x) for x in sets[2] - sets[1])
                mismatches.append({
                    "assignment_id": str(asgn_id),
                    "only_in_attempt1": only_in_1,
                    "only_in_attempt2": only_in_2,
                })

        if not mismatches:
            return make_result(
                check_id, STATUS_PASS,
                "Attempt2 question sets: all match Attempt1",
            )
        ids = [m["assignment_id"] for m in mismatches]
        return make_result(
            check_id, STATUS_FAIL,
            f"Attempt2 question set mismatch: {len(mismatches)} assignment(s) "
            f"(IDs: {', '.join(ids)})",
            mismatches,
        )
    except Exception as exc:
        return make_result(check_id, STATUS_FAIL, f"Check error: {exc}")


# ---------------------------------------------------------------------------
# Check 5 — Questions without exactly 4 answers
# ---------------------------------------------------------------------------

async def check_questions_without_4_answers(
    session: AsyncSession, sqlite: bool
) -> Dict[str, Any]:
    """Every question must have exactly 4 answer options."""
    check_id = "questions_without_4_answers"
    try:
        for tbl in ("questions", "question_answers"):
            if not await _table_exists(session, tbl, sqlite):
                return make_result(
                    check_id, STATUS_WARN,
                    f"Table '{tbl}' does not exist — skipping",
                )

        q = text(
            f"""
            SELECT q.id, COUNT(a.id) AS acount
            FROM   questions q
            LEFT   JOIN question_answers a ON a.question_id = q.id
            GROUP  BY q.id
            HAVING COUNT(a.id) != {EXPECTED_ANSWERS_PER_QUESTION}
            """
        )
        rows = (await session.execute(q)).fetchall()
        if not rows:
            return make_result(
                check_id, STATUS_PASS,
                f"Questions without {EXPECTED_ANSWERS_PER_QUESTION} answers: 0 found",
            )
        bad = [{"question_id": str(r[0]), "answer_count": r[1]} for r in rows]
        ids = [str(r[0]) for r in rows]
        return make_result(
            check_id, STATUS_FAIL,
            f"Questions without {EXPECTED_ANSWERS_PER_QUESTION} answers: "
            f"{len(rows)} found (IDs: {', '.join(ids)})",
            bad,
        )
    except Exception as exc:
        return make_result(check_id, STATUS_FAIL, f"Check error: {exc}")


# ---------------------------------------------------------------------------
# Check 6 — Questions without exactly 1 correct answer
# ---------------------------------------------------------------------------

async def check_questions_without_1_correct_answer(
    session: AsyncSession, sqlite: bool
) -> Dict[str, Any]:
    """Every question must have exactly 1 answer marked as correct."""
    check_id = "questions_without_1_correct_answer"
    try:
        for tbl in ("questions", "question_answers"):
            if not await _table_exists(session, tbl, sqlite):
                return make_result(
                    check_id, STATUS_WARN,
                    f"Table '{tbl}' does not exist — skipping",
                )

        # SQLite stores booleans as integers (1/0)
        correct_filter = "a.is_correct = 1" if sqlite else "a.is_correct = TRUE"
        q = text(
            f"""
            SELECT q.id, COUNT(a.id) AS correct_count
            FROM   questions q
            LEFT   JOIN question_answers a
                   ON  a.question_id = q.id
                   AND {correct_filter}
            GROUP  BY q.id
            HAVING COUNT(a.id) != 1
            """
        )
        rows = (await session.execute(q)).fetchall()
        if not rows:
            return make_result(
                check_id, STATUS_PASS,
                "Questions without exactly 1 correct answer: 0 found",
            )
        bad = [{"question_id": str(r[0]), "correct_count": r[1]} for r in rows]
        ids = [str(r[0]) for r in rows]
        return make_result(
            check_id, STATUS_FAIL,
            f"Questions without exactly 1 correct answer: "
            f"{len(rows)} found (IDs: {', '.join(ids)})",
            bad,
        )
    except Exception as exc:
        return make_result(check_id, STATUS_FAIL, f"Check error: {exc}")


# ---------------------------------------------------------------------------
# Check 7 — Duplicate attempts
# ---------------------------------------------------------------------------

async def check_duplicate_attempts(
    session: AsyncSession, sqlite: bool
) -> Dict[str, Any]:
    """No two rows in test_attempts may share (employee_id, topic_id, attempt_number)."""
    check_id = "duplicate_attempts"
    try:
        if not await _table_exists(session, "test_attempts", sqlite):
            return make_result(
                check_id, STATUS_WARN,
                "Table 'test_attempts' does not exist — skipping",
            )

        q = text(
            """
            SELECT employee_id, topic_id, attempt_number, COUNT(*) AS cnt
            FROM   test_attempts
            GROUP  BY employee_id, topic_id, attempt_number
            HAVING COUNT(*) > 1
            """
        )
        rows = (await session.execute(q)).fetchall()
        if not rows:
            return make_result(check_id, STATUS_PASS, "Duplicate attempts: 0 found")
        bad = [
            {
                "employee_id":    str(r[0]),
                "topic_id":       str(r[1]),
                "attempt_number": r[2],
                "count":          r[3],
            }
            for r in rows
        ]
        return make_result(
            check_id, STATUS_FAIL,
            f"Duplicate attempts: {len(rows)} duplicate group(s) found",
            bad,
        )
    except Exception as exc:
        return make_result(check_id, STATUS_FAIL, f"Check error: {exc}")


# ---------------------------------------------------------------------------
# Check 8 — Completed attempts without 15 final question states
# ---------------------------------------------------------------------------

async def check_completed_attempts_question_states(
    session: AsyncSession, sqlite: bool
) -> Dict[str, Any]:
    """
    Every COMPLETED test_attempt must have exactly 15 attempt_questions,
    all with status ANSWERED or TIMEOUT.
    """
    check_id = "completed_attempts_question_states"
    try:
        for tbl in ("test_attempts", "attempt_questions"):
            if not await _table_exists(session, tbl, sqlite):
                return make_result(
                    check_id, STATUS_WARN,
                    f"Table '{tbl}' does not exist — skipping",
                )

        # Sub-check A: wrong total count
        q_count = text(
            f"""
            SELECT ta.id, COUNT(aq.id) AS qcount
            FROM   test_attempts     ta
            JOIN   attempt_questions aq ON aq.attempt_id = ta.id
            WHERE  ta.status = 'COMPLETED'
            GROUP  BY ta.id
            HAVING COUNT(aq.id) != {EXPECTED_QUESTIONS_PER_ASSIGNMENT}
            """
        )
        bad_count = (await session.execute(q_count)).fetchall()

        # Sub-check B: non-terminal statuses inside a COMPLETED attempt
        q_status = text(
            """
            SELECT ta.id, aq.id AS aq_id, aq.status
            FROM   test_attempts     ta
            JOIN   attempt_questions aq ON aq.attempt_id = ta.id
            WHERE  ta.status = 'COMPLETED'
              AND  aq.status NOT IN ('ANSWERED', 'TIMEOUT')
            """
        )
        bad_status = (await session.execute(q_status)).fetchall()

        issues: List[str] = []
        if bad_count:
            ids = [str(r[0]) for r in bad_count]
            issues.append(f"wrong question count in attempt IDs: {', '.join(ids)}")
        if bad_status:
            attempt_ids = list(dict.fromkeys(str(r[0]) for r in bad_status))
            issues.append(
                f"non-terminal question statuses in attempt IDs: "
                f"{', '.join(attempt_ids)}"
            )

        if not issues:
            return make_result(
                check_id, STATUS_PASS,
                "Completed attempts: all have 15 ANSWERED/TIMEOUT questions",
            )

        detail = {
            "wrong_count": [
                {"attempt_id": str(r[0]), "count": r[1]} for r in bad_count
            ],
            "bad_status": [
                {
                    "attempt_id":         str(r[0]),
                    "attempt_question_id": str(r[1]),
                    "status":             r[2],
                }
                for r in bad_status
            ],
        }
        return make_result(
            check_id, STATUS_FAIL,
            f"Completed attempts with invalid question states: {'; '.join(issues)}",
            detail,
        )
    except Exception as exc:
        return make_result(check_id, STATUS_FAIL, f"Check error: {exc}")


# ---------------------------------------------------------------------------
# Check 9 — Invalid scores
# ---------------------------------------------------------------------------

async def check_invalid_scores(
    session: AsyncSession, sqlite: bool
) -> Dict[str, Any]:
    """Scores must be in the closed interval [0, 15]."""
    check_id = "invalid_scores"
    try:
        if not await _table_exists(session, "test_attempts", sqlite):
            return make_result(
                check_id, STATUS_WARN,
                "Table 'test_attempts' does not exist — skipping",
            )

        q = text(
            f"""
            SELECT id, score
            FROM   test_attempts
            WHERE  score IS NOT NULL
              AND  (score < 0 OR score > {EXPECTED_QUESTIONS_PER_ASSIGNMENT})
            """
        )
        rows = (await session.execute(q)).fetchall()
        if not rows:
            return make_result(
                check_id, STATUS_PASS,
                f"Invalid scores: 0 found "
                f"(valid range 0–{EXPECTED_QUESTIONS_PER_ASSIGNMENT})",
            )
        bad = [{"attempt_id": str(r[0]), "score": r[1]} for r in rows]
        ids = [str(r[0]) for r in rows]
        return make_result(
            check_id, STATUS_FAIL,
            f"Invalid scores: {len(rows)} found (IDs: {', '.join(ids)})",
            bad,
        )
    except Exception as exc:
        return make_result(check_id, STATUS_FAIL, f"Check error: {exc}")


# ---------------------------------------------------------------------------
# Check 10 — Broken topic sequence
# ---------------------------------------------------------------------------

async def check_topic_sequence_order(
    session: AsyncSession, sqlite: bool
) -> Dict[str, Any]:
    """
    sequence_order values for topics must form a gapless 1-based sequence
    (1, 2, 3, …, N) with no duplicates and no gaps.
    """
    check_id = "topic_sequence_order"
    try:
        if not await _table_exists(session, "topics", sqlite):
            return make_result(
                check_id, STATUS_WARN,
                "Table 'topics' does not exist — skipping",
            )

        q = text("SELECT sequence_order FROM topics ORDER BY sequence_order")
        rows = (await session.execute(q)).fetchall()
        if not rows:
            return make_result(
                check_id, STATUS_WARN,
                "Topic sequence: no topics found",
            )

        orders = [r[0] for r in rows]
        expected = list(range(1, len(orders) + 1))
        if orders == expected:
            return make_result(
                check_id, STATUS_PASS,
                f"Topic sequence order: gapless 1–{len(orders)}",
            )

        missing = sorted(set(expected) - set(orders))
        seen: set = set()
        duplicates: List[int] = []
        for o in orders:
            if o in seen:
                duplicates.append(o)
            seen.add(o)
        duplicates = sorted(set(duplicates))

        detail = {
            "found":      orders,
            "missing":    missing,
            "duplicates": duplicates,
        }
        issues: List[str] = []
        if min(orders) != 1:
            issues.append(
                f"sequence does not start at 1 (starts at {min(orders)})"
            )
        if missing:
            issues.append(f"missing positions: {missing}")
        if duplicates:
            issues.append(f"duplicate positions: {duplicates}")

        return make_result(
            check_id, STATUS_FAIL,
            f"Broken topic sequence: {'; '.join(issues)}",
            detail,
        )
    except Exception as exc:
        return make_result(check_id, STATUS_FAIL, f"Check error: {exc}")


# ---------------------------------------------------------------------------
# Check 11 — AttemptQuestions missing started_at
# ---------------------------------------------------------------------------

async def check_attempt_questions_missing_started_at(
    session: AsyncSession, sqlite: bool
) -> Dict[str, Any]:
    """
    Any attempt_question that is not PENDING must have started_at populated.
    A NULL started_at on a non-PENDING row indicates the timing state was
    never recorded.
    """
    check_id = "attempt_questions_missing_started_at"
    try:
        if not await _table_exists(session, "attempt_questions", sqlite):
            return make_result(
                check_id, STATUS_WARN,
                "Table 'attempt_questions' does not exist — skipping",
            )

        q = text(
            """
            SELECT id, status
            FROM   attempt_questions
            WHERE  status != 'PENDING'
              AND  started_at IS NULL
            """
        )
        rows = (await session.execute(q)).fetchall()
        if not rows:
            return make_result(
                check_id, STATUS_PASS,
                "Attempt questions missing started_at: 0 found",
            )
        bad = [{"id": str(r[0]), "status": r[1]} for r in rows]
        ids = [str(r[0]) for r in rows]
        return make_result(
            check_id, STATUS_FAIL,
            f"Attempt questions missing started_at: "
            f"{len(rows)} found (IDs: {', '.join(ids)})",
            bad,
        )
    except Exception as exc:
        return make_result(check_id, STATUS_FAIL, f"Check error: {exc}")


# ---------------------------------------------------------------------------
# Check 12 — ANSWERED without selected_answer_id
# ---------------------------------------------------------------------------

async def check_answered_without_selected_answer(
    session: AsyncSession, sqlite: bool
) -> Dict[str, Any]:
    """
    attempt_questions with status=ANSWERED must always have
    selected_answer_id set; a NULL here means the answer was never recorded.
    """
    check_id = "answered_without_selected_answer"
    try:
        if not await _table_exists(session, "attempt_questions", sqlite):
            return make_result(
                check_id, STATUS_WARN,
                "Table 'attempt_questions' does not exist — skipping",
            )

        q = text(
            """
            SELECT id, attempt_id
            FROM   attempt_questions
            WHERE  status = 'ANSWERED'
              AND  selected_answer_id IS NULL
            """
        )
        rows = (await session.execute(q)).fetchall()
        if not rows:
            return make_result(
                check_id, STATUS_PASS,
                "ANSWERED questions without selected_answer_id: 0 found",
            )
        bad = [{"id": str(r[0]), "attempt_id": str(r[1])} for r in rows]
        ids = [str(r[0]) for r in rows]
        return make_result(
            check_id, STATUS_FAIL,
            f"ANSWERED questions without selected_answer_id: "
            f"{len(rows)} found (IDs: {', '.join(ids)})",
            bad,
        )
    except Exception as exc:
        return make_result(check_id, STATUS_FAIL, f"Check error: {exc}")


# ---------------------------------------------------------------------------
# Check 13 — REGISTERED employees without branch
# ---------------------------------------------------------------------------

async def check_registered_employees_without_branch(
    session: AsyncSession, sqlite: bool
) -> Dict[str, Any]:
    """
    An employee in REGISTERED state must always have a branch_id.
    A NULL branch on a REGISTERED employee indicates incomplete onboarding.
    """
    check_id = "registered_employees_without_branch"
    try:
        if not await _table_exists(session, "employees", sqlite):
            return make_result(
                check_id, STATUS_WARN,
                "Table 'employees' does not exist — skipping",
            )

        q = text(
            """
            SELECT id, full_name
            FROM   employees
            WHERE  state = 'REGISTERED'
              AND  branch_id IS NULL
            """
        )
        rows = (await session.execute(q)).fetchall()
        if not rows:
            return make_result(
                check_id, STATUS_PASS,
                "REGISTERED employees without branch: 0 found",
            )
        bad = [{"id": str(r[0]), "full_name": r[1]} for r in rows]
        ids = [str(r[0]) for r in rows]
        return make_result(
            check_id, STATUS_FAIL,
            f"REGISTERED employees without branch: "
            f"{len(rows)} found (IDs: {', '.join(ids)})",
            bad,
        )
    except Exception as exc:
        return make_result(check_id, STATUS_FAIL, f"Check error: {exc}")


# ---------------------------------------------------------------------------
# Row-count summary
# ---------------------------------------------------------------------------

CRITICAL_TABLES: List[str] = [
    "admins",
    "branches",
    "employees",
    "topics",
    "questions",
    "question_answers",
    "employee_topic_assignments",
    "employee_topic_questions",
    "test_attempts",
    "attempt_questions",
    "audit_logs",
]


async def collect_row_counts(
    session: AsyncSession, sqlite: bool
) -> Dict[str, Optional[int]]:
    counts: Dict[str, Optional[int]] = {}
    for table in CRITICAL_TABLES:
        counts[table] = await _safe_count(session, table, sqlite)
    return counts


# ---------------------------------------------------------------------------
# Check registry
# ---------------------------------------------------------------------------

# Each entry: (check_id, coroutine_function, [associated_table_names])
CHECKS: List[Tuple[str, Any, List[str]]] = [
    (
        "orphan_employees",
        check_orphan_employees,
        ["employees", "branches"],
    ),
    (
        "orphan_attempts",
        check_orphan_attempts,
        ["test_attempts", "employees", "topics"],
    ),
    (
        "assignment_question_counts",
        check_assignment_question_counts,
        ["employee_topic_assignments", "employee_topic_questions"],
    ),
    (
        "attempt2_question_set",
        check_attempt2_question_set,
        ["test_attempts", "attempt_questions"],
    ),
    (
        "questions_without_4_answers",
        check_questions_without_4_answers,
        ["questions", "question_answers"],
    ),
    (
        "questions_without_1_correct_answer",
        check_questions_without_1_correct_answer,
        ["questions", "question_answers"],
    ),
    (
        "duplicate_attempts",
        check_duplicate_attempts,
        ["test_attempts"],
    ),
    (
        "completed_attempts_question_states",
        check_completed_attempts_question_states,
        ["test_attempts", "attempt_questions"],
    ),
    (
        "invalid_scores",
        check_invalid_scores,
        ["test_attempts"],
    ),
    (
        "topic_sequence_order",
        check_topic_sequence_order,
        ["topics"],
    ),
    (
        "attempt_questions_missing_started_at",
        check_attempt_questions_missing_started_at,
        ["attempt_questions"],
    ),
    (
        "answered_without_selected_answer",
        check_answered_without_selected_answer,
        ["attempt_questions"],
    ),
    (
        "registered_employees_without_branch",
        check_registered_employees_without_branch,
        ["employees"],
    ),
]


def _check_matches_table_filter(
    associated_tables: List[str], table_filter: Optional[str]
) -> bool:
    if table_filter is None:
        return True
    return any(table_filter.lower() in t.lower() for t in associated_tables)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

DIVIDER = "=" * 56


def _status_label(status: str) -> str:
    label = f"[{status:<4}]"
    return _colour(status, label)


def print_text_report(
    results: List[Dict[str, Any]],
    row_counts: Dict[str, Optional[int]],
    run_at: str,
) -> None:
    bold = COLOURS["BOLD"] if _USE_COLOUR else ""
    reset = COLOURS["RESET"] if _USE_COLOUR else ""

    print(DIVIDER)
    print(f"{bold}eco-chat.uz DATA INTEGRITY VERIFICATION{reset}")
    print(run_at)
    print(DIVIDER)

    for r in results:
        label = _status_label(r["status"])
        print(f"{label} {r['message']}")

    # ---- Row count table ----
    print(DIVIDER)
    print("ROW COUNTS:")
    max_len = max((len(t) for t in row_counts), default=10)
    for table, cnt in row_counts.items():
        cnt_str = str(cnt) if cnt is not None else "(missing)"
        print(f"  {table:<{max_len + 2}}: {cnt_str}")

    # ---- Tally ----
    total_pass = sum(1 for r in results if r["status"] == STATUS_PASS)
    total_fail = sum(1 for r in results if r["status"] == STATUS_FAIL)
    total_warn = sum(1 for r in results if r["status"] == STATUS_WARN)
    total_skip = sum(1 for r in results if r["status"] == STATUS_SKIP)

    print(DIVIDER)
    parts = [
        _colour(STATUS_PASS, f"{total_pass} PASS"),
        _colour(STATUS_FAIL, f"{total_fail} FAIL"),
        _colour(STATUS_WARN, f"{total_warn} WARN"),
    ]
    if total_skip:
        parts.append(_colour(STATUS_SKIP, f"{total_skip} SKIP"))
    print(f"RESULT: {', '.join(parts)}")
    print(DIVIDER)


def print_json_report(
    results: List[Dict[str, Any]],
    row_counts: Dict[str, Optional[int]],
    run_at: str,
) -> None:
    total_pass = sum(1 for r in results if r["status"] == STATUS_PASS)
    total_fail = sum(1 for r in results if r["status"] == STATUS_FAIL)
    total_warn = sum(1 for r in results if r["status"] == STATUS_WARN)
    total_skip = sum(1 for r in results if r["status"] == STATUS_SKIP)

    report = {
        "project": "eco-chat.uz",
        "run_at": run_at,
        "summary": {
            "pass":    total_pass,
            "fail":    total_fail,
            "warn":    total_warn,
            "skip":    total_skip,
            "overall": "FAIL" if total_fail > 0 else "PASS",
        },
        "checks":     results,
        "row_counts": row_counts,
    }
    print(json.dumps(report, indent=2, default=str))


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

async def run_checks(
    table_filter: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Optional[int]]]:
    url = _get_database_url()
    sqlite = _is_sqlite(url)

    engine = create_async_engine(url, echo=False, future=True)
    AsyncSessionLocal = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    results: List[Dict[str, Any]] = []
    row_counts: Dict[str, Optional[int]] = {}

    async with AsyncSessionLocal() as session:
        for check_id, check_fn, tables in CHECKS:
            if not _check_matches_table_filter(tables, table_filter):
                results.append(
                    make_result(
                        check_id,
                        STATUS_SKIP,
                        f"Skipped (table filter: '{table_filter}')",
                    )
                )
                continue
            result = await check_fn(session, sqlite)
            results.append(result)

        row_counts = await collect_row_counts(session, sqlite)

    await engine.dispose()
    return results, row_counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="verify_data_integrity",
        description="eco-chat.uz data integrity verification tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python verify_data_integrity.py\n"
            "  python verify_data_integrity.py --json\n"
            "  python verify_data_integrity.py --table employees\n"
            "  python verify_data_integrity.py --json --table attempts\n"
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output results as JSON instead of human-readable text",
    )
    parser.add_argument(
        "--table",
        metavar="TABLE_NAME",
        default=None,
        help=(
            "Only run checks associated with the given table name "
            "(substring match, case-insensitive)"
        ),
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    run_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        results, row_counts = await run_checks(table_filter=args.table)
    except Exception as exc:
        error_payload = {
            "project": "eco-chat.uz",
            "run_at": run_at,
            "fatal_error": str(exc),
        }
        if args.output_json:
            print(json.dumps(error_payload, indent=2))
        else:
            print(f"\n[FATAL] Could not connect to or query the database:\n  {exc}\n")
        return 1

    if args.output_json:
        print_json_report(results, row_counts, run_at)
    else:
        print_text_report(results, row_counts, run_at)

    any_fail = any(r["status"] == STATUS_FAIL for r in results)
    return 1 if any_fail else 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
