"""
eco-chat.uz — Core Test Engine (Single Source of Truth)
====================================================
This module is THE canonical business logic for:
  - Question assignment (15 fixed questions per employee+topic)
  - Attempt lifecycle management (start, answer, timeout, complete)
  - Server-side timer validation
  - Knowledge growth calculation
  - All critical invariants enforced here

Web API and Telegram Bot both call this service — no duplicate logic.
"""

from __future__ import annotations

import random
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, and_

from app.models.attempt import (
    TestAttempt,
    EmployeeTopicAssignment,
    EmployeeTopicQuestion,
    AttemptQuestion,
)
from app.models.question import Question, QuestionAnswer
from app.models.topic import Topic
from app.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _utc_now() -> datetime:
    """Always return UTC-aware datetime for timer calculations."""
    return datetime.now(timezone.utc)


def _make_aware(dt: datetime) -> datetime:
    """
    Convert naive datetime (from SQLite) to UTC-aware.
    If already aware, return as-is.
    SQLite stores datetimes WITHOUT timezone info — this normalizes them.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _shuffle_different(lst: list, reference: Optional[list] = None, max_tries: int = 100) -> list:
    """
    Return a shuffled copy of lst that differs from reference (if provided).
    Guarantees different order for attempt 2 vs attempt 1.
    """
    shuffled = lst.copy()
    if reference is None:
        random.shuffle(shuffled)
        return shuffled

    for _ in range(max_tries):
        random.shuffle(shuffled)
        if shuffled != reference:
            return shuffled

    # Fallback: force swap first two elements to guarantee difference
    if len(shuffled) >= 2:
        shuffled[0], shuffled[1] = shuffled[1], shuffled[0]
    logger.warning("Shuffle fallback used (rare statistical case)")
    return shuffled


# ─────────────────────────────────────────────────────────────────────────────
#  ASSIGNMENT — 15 Fixed Questions per Employee+Topic
# ─────────────────────────────────────────────────────────────────────────────

async def get_or_create_assignment(
    db: AsyncSession,
    employee_id: str,
    topic_id: str,
) -> EmployeeTopicAssignment:
    """
    Get existing assignment or create one.
    If new: atomically selects 15 unique ACTIVE questions.
    Uses SELECT FOR UPDATE to prevent race conditions.
    This is TRANSACTIONAL — all 15 questions or none.
    """
    # Always use str() for UUID comparisons — works for both SQLite and PostgreSQL
    eid = str(employee_id)
    tid = str(topic_id)

    # SELECT FOR UPDATE prevents duplicate assignments
    result = await db.execute(
        select(EmployeeTopicAssignment)
        .where(
            and_(
                EmployeeTopicAssignment.employee_id == eid,
                EmployeeTopicAssignment.topic_id == tid,
            )
        )
        .with_for_update()
    )
    assignment = result.scalar_one_or_none()

    if assignment:
        return assignment

    # Create new assignment
    assignment = EmployeeTopicAssignment(
        employee_id=eid,
        topic_id=tid,
        status="ASSIGNED",
    )
    db.add(assignment)
    await db.flush()  # Get assignment.id before creating questions

    # Select 15 unique ACTIVE questions
    questions_result = await db.execute(
        select(Question)
        .where(
            and_(
                Question.topic_id == tid,
                Question.status == "ACTIVE",
            )
        )
    )
    all_active_questions = questions_result.scalars().all()

    if len(all_active_questions) < settings.min_questions_per_topic:
        await db.rollback()
        raise ValueError(
            f"Topic has only {len(all_active_questions)} active questions. "
            f"Minimum {settings.min_questions_per_topic} required."
        )

    # Random sample — this is the ONE AND ONLY time we randomly select
    selected_questions = random.sample(all_active_questions, settings.min_questions_per_topic)

    # Create immutable snapshots (even if question is later archived)
    for slot, question in enumerate(selected_questions, start=1):
        # Fetch answers for this question
        answers_result = await db.execute(
            select(QuestionAnswer).where(QuestionAnswer.question_id == question.id)
        )
        answers = answers_result.scalars().all()

        if len(answers) != 4:
            await db.rollback()
            raise ValueError(
                f"Question {question.id} has {len(answers)} answers (expected 4). "
                "DB integrity error."
            )

        correct_answers = [a for a in answers if a.is_correct]
        if len(correct_answers) != 1:
            await db.rollback()
            raise ValueError(
                f"Question {question.id} has {len(correct_answers)} correct answers (expected 1). "
                "DB integrity error."
            )

        correct_answer = correct_answers[0]

        # Build snapshot (preserves text even if question is later archived)
        answers_snapshot = [
            {
                "id": str(a.id),
                "label": a.option_label,
                "text": a.text,
                "is_correct": a.is_correct,
            }
            for a in sorted(answers, key=lambda x: x.sort_order)
        ]

        etq = EmployeeTopicQuestion(
            assignment_id=assignment.id,
            question_id=question.id,
            base_slot=slot,
            question_text_snapshot=question.text,
            answers_snapshot=answers_snapshot,
            correct_answer_id=correct_answer.id,
        )
        db.add(etq)

    await db.commit()
    await db.refresh(assignment)
    logger.info(
        "Created assignment: employee=%s topic=%s questions=15",
        employee_id,
        topic_id,
    )
    return assignment


# ─────────────────────────────────────────────────────────────────────────────
#  CAN START ATTEMPT — Full Business Rule Validation
# ─────────────────────────────────────────────────────────────────────────────

async def can_start_attempt(
    db: AsyncSession,
    employee_id: str,
    topic_id: str,
    attempt_number: int,
) -> tuple[bool, str]:
    """
    Validate all business rules before starting an attempt.
    Returns (can_start: bool, reason: str).
    
    Rules checked:
    1. attempt_number must be 1 or 2
    2. No duplicate attempt (DB unique constraint + service check)
    3. Topic must be unlocked (previous topic fully completed)
    4. Topic must have >= 15 active questions
    5. If attempt_number == 2:
       - attempt 1 must be COMPLETED
       - at least 10 minutes since attempt 1 completion
       - seminar must be confirmed
    """
    if attempt_number not in (1, 2):
        return False, f"Invalid attempt number: {attempt_number}. Must be 1 or 2."

    # Check for existing attempt with same number (would violate unique constraint)
    existing = await db.execute(
        select(TestAttempt).where(
            and_(
                TestAttempt.employee_id == employee_id,
                TestAttempt.topic_id == topic_id,
                TestAttempt.attempt_number == attempt_number,
            )
        )
    )
    if existing.scalar_one_or_none():
        return False, f"Attempt {attempt_number} already exists for this topic."

    # Check topic is unlocked (sequence validation)
    topic_result = await db.execute(
        select(Topic).where(Topic.id == topic_id)
    )
    topic = topic_result.scalar_one_or_none()
    if not topic:
        return False, "Topic not found."
    if not topic.is_active:
        return False, "Topic is not active."

    # Check sequence: all previous topics must have both attempts COMPLETED
    if topic.sequence_order > 1:
        prev_topics_result = await db.execute(
            select(Topic).where(
                and_(
                    Topic.sequence_order < topic.sequence_order,
                    Topic.is_active == True,
                )
            )
        )
        prev_topics = prev_topics_result.scalars().all()

        for prev_topic in prev_topics:
            assignment_result = await db.execute(
                select(EmployeeTopicAssignment).where(
                    and_(
                        EmployeeTopicAssignment.employee_id == employee_id,
                        EmployeeTopicAssignment.topic_id == prev_topic.id,
                        EmployeeTopicAssignment.status == "COMPLETED",
                    )
                )
            )
            if not assignment_result.scalar_one_or_none():
                return False, f"Topic '{prev_topic.short_name}' must be completed first."

    # Check topic has enough questions (for attempt 1 — attempt 2 uses existing assignment)
    if attempt_number == 1:
        from app.services.topic_service import get_topic_active_question_count
        q_count = await get_topic_active_question_count(db, topic_id)
        if q_count < settings.min_questions_per_topic:
            return False, (
                f"Topic has only {q_count} active questions. "
                f"Need at least {settings.min_questions_per_topic}."
            )

    # Attempt 2 specific rules
    if attempt_number == 2:
        assignment_result = await db.execute(
            select(EmployeeTopicAssignment).where(
                and_(
                    EmployeeTopicAssignment.employee_id == employee_id,
                    EmployeeTopicAssignment.topic_id == topic_id,
                )
            )
        )
        assignment = assignment_result.scalar_one_or_none()
        if not assignment:
            return False, "No assignment found. Start attempt 1 first."

        # Attempt 1 must be completed
        if not assignment.attempt1_id:
            return False, "Attempt 1 not started."

        attempt1_result = await db.execute(
            select(TestAttempt).where(TestAttempt.id == assignment.attempt1_id)
        )
        attempt1 = attempt1_result.scalar_one_or_none()

        if not attempt1 or attempt1.status != "COMPLETED":
            return False, "Attempt 1 must be completed before starting attempt 2."

        # 10-minute gate (hidden from user — natural UX message used instead)
        min_wait = timedelta(seconds=settings.attempt2_min_wait_seconds)
        earliest_start = _make_aware(attempt1.completed_at) + min_wait
        now = _utc_now()

        if now < earliest_start:
            remaining = int((earliest_start - now).total_seconds())
            return False, f"NOT_YET_READY:{remaining}"

        # Seminar confirmation required - Bypassed as per user request to unlock purely based on 10-minute timer
        # if not assignment.seminar_confirmed:
        #     return False, "SEMINAR_NOT_CONFIRMED"

    return True, "OK"


# ─────────────────────────────────────────────────────────────────────────────
#  START ATTEMPT
# ─────────────────────────────────────────────────────────────────────────────

async def start_attempt(
    db: AsyncSession,
    redis,
    employee_id: str,
    topic_id: str,
    attempt_number: int,
) -> TestAttempt:
    """
    Create a new attempt with shuffled question and answer order.
    
    For attempt 1:
    - Calls get_or_create_assignment (selects 15 random questions once)
    - Creates shuffled presentation

    For attempt 2:
    - Reads SAME 15 questions from assignment (no new selection)
    - Creates DIFFERENT shuffled presentation:
      * Question order guaranteed different from attempt 1
      * Per-question answer order guaranteed different from attempt 1
    
    ALL IN ONE TRANSACTION.
    """
    # Validate first
    can_start, reason = await can_start_attempt(db, employee_id, topic_id, attempt_number)
    if not can_start:
        raise PermissionError(f"Cannot start attempt: {reason}")

    # Get or create assignment (idempotent — 15 questions selected only once)
    assignment = await get_or_create_assignment(db, employee_id, topic_id)

    # Create the attempt record
    attempt = TestAttempt(
        employee_id=employee_id,
        topic_id=topic_id,
        assignment_id=assignment.id,
        attempt_number=attempt_number,
        status="IN_PROGRESS",
        current_question_index=1,
        score=0,
    )
    db.add(attempt)
    await db.flush()

    # Link attempt to assignment
    if attempt_number == 1:
        assignment.attempt1_id = attempt.id
        assignment.status = "ATTEMPT1_IN_PROGRESS"
    else:
        assignment.attempt2_id = attempt.id
        assignment.status = "ATTEMPT2_IN_PROGRESS"

    # Fetch the 15 fixed questions for this assignment
    etqs_result = await db.execute(
        select(EmployeeTopicQuestion)
        .where(EmployeeTopicQuestion.assignment_id == assignment.id)
        .order_by(EmployeeTopicQuestion.base_slot)
    )
    etqs = etqs_result.scalars().all()

    if len(etqs) != 15:
        await db.rollback()
        raise ValueError(
            f"Assignment has {len(etqs)} questions instead of 15. Data integrity error."
        )

    # Get attempt 1 order (for attempt 2 shuffle comparison)
    attempt1_question_order = None
    attempt1_answer_orders = {}

    if attempt_number == 2 and assignment.attempt1_id:
        aq1_result = await db.execute(
            select(AttemptQuestion)
            .where(AttemptQuestion.attempt_id == assignment.attempt1_id)
            .order_by(AttemptQuestion.display_order)
        )
        aq1s = aq1_result.scalars().all()
        attempt1_question_order = [str(aq.assignment_question_id) for aq in aq1s]
        attempt1_answer_orders = {
            str(aq.assignment_question_id): aq.answer_display_order
            for aq in aq1s
        }

    # Build shuffled question display order
    etq_ids = [str(etq.id) for etq in etqs]
    shuffled_etq_ids = _shuffle_different(etq_ids, attempt1_question_order)

    # Create AttemptQuestion records
    now = _utc_now()
    first_question = True

    for display_pos, etq_id in enumerate(shuffled_etq_ids, start=1):
        # Find the ETQ object
        etq = next(e for e in etqs if str(e.id) == etq_id)

        # Build answer display order
        answer_ids = [a["id"] for a in etq.answers_snapshot]
        prev_answer_order = attempt1_answer_orders.get(etq_id)
        shuffled_answer_ids = _shuffle_different(answer_ids, prev_answer_order)

        # Build display-order answer list
        answer_display_order = []
        for display_label_idx, answer_id in enumerate(shuffled_answer_ids):
            display_label = ["A", "B", "C", "D"][display_label_idx]
            original_answer = next(
                a for a in etq.answers_snapshot if a["id"] == answer_id
            )
            answer_display_order.append({
                "id": answer_id,
                "display_label": display_label,
                "text": original_answer["text"],
                "is_correct": original_answer["is_correct"],  # stored but NOT sent to client
            })

        # Timer: only start for first question
        if first_question:
            q_started_at = now
            q_deadline_at = now + timedelta(seconds=settings.question_timer_seconds)
            first_question = False
        else:
            q_started_at = None
            q_deadline_at = None

        aq = AttemptQuestion(
            attempt_id=attempt.id,
            assignment_question_id=etq.id,
            question_id=etq.question_id,
            display_order=display_pos,
            answer_display_order=answer_display_order,
            question_started_at=q_started_at,
            question_deadline_at=q_deadline_at,
            answer_status="PENDING",
        )
        db.add(aq)

    await db.commit()
    await db.refresh(attempt)
    logger.info(
        "Started attempt: employee=%s topic=%s attempt=%d id=%s",
        employee_id,
        topic_id,
        attempt_number,
        attempt.id,
    )
    return attempt


# ─────────────────────────────────────────────────────────────────────────────
#  GET CURRENT QUESTION
# ─────────────────────────────────────────────────────────────────────────────

async def get_current_question(
    db: AsyncSession,
    attempt_id: str,
) -> Optional[dict]:
    """
    Return the current active question with shuffled answers and remaining time.
    Handles expired questions automatically (auto-timeout and advance).
    Returns None if attempt is completed.
    """
    attempt = (
        await db.execute(select(TestAttempt).where(TestAttempt.id == attempt_id))
    ).scalar_one_or_none()

    if not attempt or attempt.status == "COMPLETED":
        return None

    # Check for expired questions that haven't been marked yet
    await _process_expired_questions(db, attempt)

    # Reload attempt after potential progression
    await db.refresh(attempt)
    if attempt.status == "COMPLETED":
        return None

    # Get current question
    aq = (
        await db.execute(
            select(AttemptQuestion).where(
                and_(
                    AttemptQuestion.attempt_id == attempt_id,
                    AttemptQuestion.display_order == attempt.current_question_index,
                )
            )
        )
    ).scalar_one_or_none()

    if not aq:
        return None

    now = _utc_now()
    remaining_seconds = 0
    if aq.question_deadline_at:
        remaining_seconds = max(0, int((_make_aware(aq.question_deadline_at) - now).total_seconds()))

    # Build answer list (WITHOUT is_correct field — never send to client)
    safe_answers = [
        {
            "id": a["id"],
            "display_label": a["display_label"],
            "text": a["text"],
        }
        for a in aq.answer_display_order
    ]

    return {
        "attempt_question_id": str(aq.id),
        "display_order": aq.display_order,
        "question_index": attempt.current_question_index,
        "total_questions": 15,
        "question_text": aq.answer_display_order,  # Will be fetched from ETQ snapshot
        "answers": safe_answers,
        "remaining_seconds": remaining_seconds,
        "answer_status": aq.answer_status,
    }


async def get_current_question_full(
    db: AsyncSession,
    attempt_id: str,
) -> Optional[dict]:
    """
    Full question data including text snapshot.
    Used by bot and API.
    """
    attempt = (
        await db.execute(select(TestAttempt).where(TestAttempt.id == attempt_id))
    ).scalar_one_or_none()

    if not attempt or attempt.status == "COMPLETED":
        return None

    # Auto-process expired questions
    await _process_expired_questions(db, attempt)
    await db.refresh(attempt)

    if attempt.status == "COMPLETED":
        return None

    aq = (
        await db.execute(
            select(AttemptQuestion).where(
                and_(
                    AttemptQuestion.attempt_id == attempt_id,
                    AttemptQuestion.display_order == attempt.current_question_index,
                )
            )
        )
    ).scalar_one_or_none()

    if not aq:
        return None

    # Get question snapshot
    etq = (
        await db.execute(
            select(EmployeeTopicQuestion).where(
                EmployeeTopicQuestion.id == aq.assignment_question_id
            )
        )
    ).scalar_one_or_none()

    now = _utc_now()
    remaining_seconds = 0
    if aq.question_deadline_at:
        remaining_seconds = max(0, int((_make_aware(aq.question_deadline_at) - now).total_seconds()))

    # Safe answers (no is_correct, no correct_answer_id)
    safe_answers = [
        {
            "id": a["id"],
            "display_label": a["display_label"],
            "text": a["text"],
        }
        for a in aq.answer_display_order
    ]

    # Query topic details for display headers in bot
    topic = (
        await db.execute(select(Topic).where(Topic.id == str(attempt.topic_id)))
    ).scalar_one_or_none()
    topic_name = f"{topic.short_name} — {topic.full_name}" if topic else "Мавзу"

    return {
        "attempt_question_id": str(aq.id),
        "display_order": aq.display_order,
        "current_index": aq.display_order,
        "question_index": attempt.current_question_index,
        "total_questions": 15,
        "question_text": etq.question_text_snapshot if etq else "",
        "answers": safe_answers,
        "remaining_seconds": remaining_seconds,
        "answer_status": aq.answer_status,
        "attempt_id": str(attempt_id),
        "attempt_number": attempt.attempt_number,
        "topic_name": topic_name,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  SUBMIT ANSWER — Idempotent + Race-condition Safe
# ─────────────────────────────────────────────────────────────────────────────

async def submit_answer(
    db: AsyncSession,
    redis,
    attempt_id: str,
    display_order: int,
    selected_answer_id: str,
) -> dict:
    """
    Submit an answer for a question.
    
    CRITICAL SAFETY PROPERTIES:
    1. Idempotent: duplicate callbacks return same result without re-processing
    2. Race-condition safe: SELECT FOR UPDATE on AttemptQuestion row
    3. Server-side timer: checks deadline_at, rejects late answers
    4. Redis idempotency key: fast first-line defense against duplicate callbacks
    """
    # Redis idempotency check (fast path — before DB lock)
    idempotency_key = f"answer:{attempt_id}:{display_order}"
    if redis:
        try:
            # NX = only set if not exists, EX = expire in 60 seconds
            already_processed = not await redis.set(
                idempotency_key, "1", nx=True, ex=60
            )
            if already_processed:
                # Duplicate callback — return current state without re-processing
                existing_aq = (
                    await db.execute(
                        select(AttemptQuestion).where(
                            and_(
                                AttemptQuestion.attempt_id == attempt_id,
                                AttemptQuestion.display_order == display_order,
                            )
                        )
                    )
                ).scalar_one_or_none()
                if existing_aq and existing_aq.answer_status != "PENDING":
                    return {
                        "is_correct": existing_aq.is_correct,
                        "answer_status": existing_aq.answer_status,
                        "attempt_completed": False,
                        "idempotent_response": True,
                    }
        except Exception as e:
            logger.warning("Redis idempotency check failed: %s. Falling back to DB.", e)

    # DB-level protection: SELECT FOR UPDATE
    aq = (
        await db.execute(
            select(AttemptQuestion)
            .where(
                and_(
                    AttemptQuestion.attempt_id == attempt_id,
                    AttemptQuestion.display_order == display_order,
                )
            )
            .with_for_update()
        )
    ).scalar_one_or_none()

    if not aq:
        return {"error": "Question not found", "answer_status": "ERROR", "attempt_completed": False}

    # Already answered (DB-level idempotency)
    if aq.answer_status != "PENDING":
        return {
            "is_correct": aq.is_correct,
            "answer_status": aq.answer_status,
            "attempt_completed": False,
            "idempotent_response": True,
        }

    now = _utc_now()

    # SERVER-SIDE TIMER CHECK (canonical)
    if aq.question_deadline_at and now > _make_aware(aq.question_deadline_at):
        # Late answer — process as timeout
        result = await _process_timeout(db, aq)
        await db.commit()
        return result

    # Validate answer belongs to this question
    etq = (
        await db.execute(
            select(EmployeeTopicQuestion).where(
                EmployeeTopicQuestion.id == aq.assignment_question_id
            )
        )
    ).scalar_one_or_none()

    if not etq:
        return {"error": "Assignment question not found", "answer_status": "ERROR", "attempt_completed": False}

    # Check if selected_answer_id is in the allowed answers for this question
    allowed_answer_ids = {a["id"] for a in aq.answer_display_order}
    if selected_answer_id not in allowed_answer_ids:
        return {"error": "Invalid answer ID", "answer_status": "ERROR", "attempt_completed": False}

    # Determine correctness from snapshot (not from live DB — for historical integrity)
    is_correct = str(etq.correct_answer_id).strip() == str(selected_answer_id).strip()
    logger.debug("Answer check: correct_id=%s selected=%s is_correct=%s",
                 etq.correct_answer_id, selected_answer_id, is_correct)

    # Record answer
    response_time_ms = int((now - _make_aware(aq.question_started_at)).total_seconds() * 1000) if aq.question_started_at else 0
    aq.answer_status = "ANSWERED"
    aq.selected_answer_id = selected_answer_id
    aq.is_correct = is_correct
    aq.answered_at = now
    aq.response_time_ms = response_time_ms

    # Get attempt and update score
    attempt = (
        await db.execute(select(TestAttempt).where(TestAttempt.id == attempt_id))
    ).scalar_one_or_none()

    if is_correct:
        attempt.score += 1

    # Fetch topic details for bot headers
    topic = (
        await db.execute(select(Topic).where(Topic.id == str(attempt.topic_id)))
    ).scalar_one_or_none()
    topic_name = f"{topic.short_name} — {topic.full_name}" if topic else "Мавзу"

    # Advance to next question
    next_question_data = None
    attempt_completed = False

    if attempt.current_question_index < 15:
        next_index = attempt.current_question_index + 1
        attempt.current_question_index = next_index

        # Start timer for next question
        next_aq = (
            await db.execute(
                select(AttemptQuestion).where(
                    and_(
                        AttemptQuestion.attempt_id == attempt_id,
                        AttemptQuestion.display_order == next_index,
                    )
                )
            )
        ).scalar_one_or_none()

        if next_aq:
            next_aq.question_started_at = now
            next_aq.question_deadline_at = now + timedelta(
                seconds=settings.question_timer_seconds
            )
            # Build next question data for bot
            safe_answers = [
                {
                    "id": a["id"],
                    "display_label": a["display_label"],
                    "text": a["text"],
                }
                for a in next_aq.answer_display_order
            ]
            next_question_data = {
                "attempt_id": attempt_id,
                "display_order": next_aq.display_order,
                "current_index": next_aq.display_order,
                "question_text": None,  # will be fetched below
                "answers": safe_answers,
                "remaining_seconds": settings.question_timer_seconds,
                "attempt_question_id": str(next_aq.id),
                "attempt_number": attempt.attempt_number,
                "topic_name": topic_name,
            }
            # Fetch question text from snapshot
            etq_next = (
                await db.execute(
                    select(EmployeeTopicQuestion).where(
                        EmployeeTopicQuestion.id == next_aq.assignment_question_id
                    )
                )
            ).scalar_one_or_none()
            if etq_next:
                next_question_data["question_text"] = etq_next.question_text_snapshot
    else:
        # All 15 questions answered
        await _complete_attempt(db, attempt)
        attempt_completed = True

    await db.commit()
    try:
        from app.services.data_guard import auto_backup_data
        await auto_backup_data(db)
    except Exception:
        pass

    return {

        "is_correct": is_correct,
        "answer_status": "ANSWERED",
        "next_question": next_question_data,
        "attempt_completed": attempt_completed,
        "score_so_far": attempt.score,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  TIMEOUT HANDLING
# ─────────────────────────────────────────────────────────────────────────────

async def _process_timeout(db: AsyncSession, aq: AttemptQuestion) -> dict:
    """Mark a question as TIMEOUT and advance to next question."""
    now = _utc_now()
    aq.answer_status = "TIMEOUT"
    aq.is_correct = False
    aq.answered_at = now

    # Get attempt
    attempt = (
        await db.execute(select(TestAttempt).where(TestAttempt.id == aq.attempt_id))
    ).scalar_one_or_none()

    if not attempt:
        return {"answer_status": "TIMEOUT", "attempt_completed": False}

    attempt_completed = False

    if attempt.current_question_index < 15:
        next_index = attempt.current_question_index + 1
        attempt.current_question_index = next_index

        next_aq = (
            await db.execute(
                select(AttemptQuestion).where(
                    and_(
                        AttemptQuestion.attempt_id == str(attempt.id),
                        AttemptQuestion.display_order == next_index,
                    )
                )
            )
        ).scalar_one_or_none()

        if next_aq and not next_aq.question_started_at:
            next_aq.question_started_at = now
            next_aq.question_deadline_at = now + timedelta(
                seconds=settings.question_timer_seconds
            )
    else:
        await _complete_attempt(db, attempt)
        attempt_completed = True

    return {
        "answer_status": "TIMEOUT",
        "attempt_completed": attempt_completed,
        "is_correct": False,
    }


async def handle_timeout(db: AsyncSession, attempt_question_id: str) -> dict:
    """Public timeout handler called by background job or bot reconnect."""
    aq = (
        await db.execute(
            select(AttemptQuestion)
            .where(AttemptQuestion.id == attempt_question_id)
            .with_for_update()
        )
    ).scalar_one_or_none()

    if not aq or aq.answer_status != "PENDING":
        return {"answer_status": aq.answer_status if aq else "NOT_FOUND", "attempt_completed": False}

    now = _utc_now()
    if aq.question_deadline_at and now <= _make_aware(aq.question_deadline_at):
        return {"answer_status": "PENDING", "attempt_completed": False, "remaining_seconds": int((_make_aware(aq.question_deadline_at) - now).total_seconds())}

    result = await _process_timeout(db, aq)
    await db.commit()
    return result


async def _process_expired_questions(db: AsyncSession, attempt: TestAttempt) -> int:
    """
    On bot reconnect or any state check:
    Auto-timeout all expired PENDING questions and advance state.
    Returns count of questions timed out.
    """
    timed_out_count = 0
    now = _utc_now()

    while attempt.status == "IN_PROGRESS":
        current_aq = (
            await db.execute(
                select(AttemptQuestion).where(
                    and_(
                        AttemptQuestion.attempt_id == str(attempt.id),
                        AttemptQuestion.display_order == attempt.current_question_index,
                    )
                )
            )
        ).scalar_one_or_none()

        if not current_aq:
            break

        if current_aq.answer_status != "PENDING":
            break

        if not current_aq.question_deadline_at:
            break

        if now <= _make_aware(current_aq.question_deadline_at):
            # Not expired yet
            break

        # Process timeout
        await _process_timeout(db, current_aq)
        timed_out_count += 1

        # Reload attempt state
        await db.refresh(attempt)

    if timed_out_count > 0:
        await db.commit()
        logger.info(
            "Auto-timed-out %d questions for attempt %s",
            timed_out_count,
            attempt.id,
        )

    return timed_out_count


async def check_and_handle_expired_questions(
    db: AsyncSession,
    attempt_id: str,
) -> int:
    """Public interface for background job / bot restart recovery."""
    attempt = (
        await db.execute(select(TestAttempt).where(TestAttempt.id == attempt_id))
    ).scalar_one_or_none()

    if not attempt or attempt.status == "COMPLETED":
        return 0

    return await _process_expired_questions(db, attempt)


# ─────────────────────────────────────────────────────────────────────────────
#  COMPLETE ATTEMPT
# ─────────────────────────────────────────────────────────────────────────────

async def _complete_attempt(db: AsyncSession, attempt: TestAttempt) -> None:
    """Internal: mark attempt as COMPLETED and update assignment."""
    now = _utc_now()
    attempt.status = "COMPLETED"
    attempt.completed_at = now

    # Update assignment status
    assignment = (
        await db.execute(
            select(EmployeeTopicAssignment).where(
                EmployeeTopicAssignment.id == attempt.assignment_id
            )
        )
    ).scalar_one_or_none()

    if assignment:
        if attempt.attempt_number == 1:
            assignment.status = "ATTEMPT1_DONE"
        elif attempt.attempt_number == 2:
            assignment.status = "COMPLETED"
            assignment.completed_at = now

    try:
        from app.services.data_guard import auto_backup_data
        await auto_backup_data(db)
    except Exception as ex:
        logger.debug("Auto backup after test completion error: %s", ex)

    # Broadcast SSE event

    try:
        from app.services.sse_service import broadcaster
        await broadcaster.broadcast(
            "attempt_completed",
            {
                "employee_id": str(attempt.employee_id),
                "topic_id": str(attempt.topic_id),
                "attempt_number": attempt.attempt_number,
                "score": attempt.score,
            },
        )
    except Exception as e:
        logger.warning("SSE broadcast failed: %s", e)


async def complete_attempt(
    db: AsyncSession,
    redis,
    attempt_id: str,
) -> TestAttempt:
    """Public interface to complete an attempt."""
    attempt = (
        await db.execute(select(TestAttempt).where(TestAttempt.id == attempt_id))
    ).scalar_one_or_none()

    if not attempt:
        raise ValueError(f"Attempt {attempt_id} not found")

    if attempt.status == "COMPLETED":
        return attempt

    await _complete_attempt(db, attempt)
    await db.commit()
    await db.refresh(attempt)
    return attempt


# ─────────────────────────────────────────────────────────────────────────────
#  RESULTS & KNOWLEDGE GROWTH
# ─────────────────────────────────────────────────────────────────────────────

async def get_attempt_results(
    db: AsyncSession,
    attempt_id: str,
) -> dict:
    """
    Return attempt results.
    IMPORTANT: Does NOT reveal correct answers — only score summary.
    """
    attempt = (
        await db.execute(select(TestAttempt).where(TestAttempt.id == attempt_id))
    ).scalar_one_or_none()

    if not attempt:
        return {}

    total = 15
    score = attempt.score
    percentage = round(score / total * 100, 2)

    return {
        "attempt_id": str(attempt_id),
        "attempt_number": attempt.attempt_number,
        "score": score,
        "total": total,
        "percentage": percentage,
        "status": attempt.status,
        "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
        # Correct answers NOT included — prevents answer banking
    }


async def get_topic_comparison(
    db: AsyncSession,
    employee_id: str,
    topic_id: str,
) -> dict:
    """
    Canonical knowledge growth calculation.
    This is THE formula used by Web, API, Excel — all in one place.
    
    knowledge_growth_pp = attempt2_pct - attempt1_pct (percentage points)
    delta_correct = attempt2_score - attempt1_score
    """
    assignment_result = await db.execute(
        select(EmployeeTopicAssignment).where(
            and_(
                EmployeeTopicAssignment.employee_id == employee_id,
                EmployeeTopicAssignment.topic_id == topic_id,
            )
        )
    )
    assignment = assignment_result.scalar_one_or_none()

    if not assignment:
        return {"status": "NOT_STARTED"}

    result = {
        "topic_id": str(topic_id),
        "assignment_status": assignment.status,
        "attempt1": None,
        "attempt2": None,
        "knowledge_growth_pp": None,
        "delta_correct": None,
    }

    total = 15

    if assignment.attempt1_id:
        a1 = (
            await db.execute(
                select(TestAttempt).where(TestAttempt.id == assignment.attempt1_id)
            )
        ).scalar_one_or_none()
        if a1:
            a1_pct = round(a1.score / total * 100, 2)
            result["attempt1"] = {
                "score": a1.score,
                "total": total,
                "percentage": a1_pct,
                "status": a1.status,
                "completed_at": a1.completed_at.isoformat() if a1.completed_at else None,
            }

    if assignment.attempt2_id:
        a2 = (
            await db.execute(
                select(TestAttempt).where(TestAttempt.id == assignment.attempt2_id)
            )
        ).scalar_one_or_none()
        if a2:
            a2_pct = round(a2.score / total * 100, 2)
            result["attempt2"] = {
                "score": a2.score,
                "total": total,
                "percentage": a2_pct,
                "status": a2.status,
                "completed_at": a2.completed_at.isoformat() if a2.completed_at else None,
            }

        # Knowledge growth (only meaningful when both attempts done)
        if result["attempt1"] and result["attempt2"]:
            a1_pct = result["attempt1"]["percentage"]
            a2_pct = result["attempt2"]["percentage"]
            result["knowledge_growth_pp"] = round(a2_pct - a1_pct, 2)
            result["delta_correct"] = a2.score - result["attempt1"]["score"]

    return result


# ─────────────────────────────────────────────────────────────────────────────
#  SEMINAR CONFIRMATION
# ─────────────────────────────────────────────────────────────────────────────

async def confirm_seminar(
    db: AsyncSession,
    employee_id: str,
    topic_id: str,
) -> dict:
    """
    Employee confirms seminar completion.
    Required before attempt 2 can start.
    """
    assignment_result = await db.execute(
        select(EmployeeTopicAssignment)
        .where(
            and_(
                EmployeeTopicAssignment.employee_id == employee_id,
                EmployeeTopicAssignment.topic_id == topic_id,
            )
        )
        .with_for_update()
    )
    assignment = assignment_result.scalar_one_or_none()

    if not assignment:
        return {"success": False, "message": "No assignment found"}

    if assignment.status != "ATTEMPT1_DONE":
        return {"success": False, "message": "Attempt 1 must be completed first"}

    # Check 10-minute gate
    if assignment.attempt1_id:
        a1 = (
            await db.execute(
                select(TestAttempt).where(TestAttempt.id == assignment.attempt1_id)
            )
        ).scalar_one_or_none()

        if a1 and a1.completed_at:
            now = _utc_now()
            elapsed = (now - _make_aware(a1.completed_at)).total_seconds()
            if elapsed < settings.attempt2_min_wait_seconds:
                # Not yet time — don't reveal the 10-min rule
                return {
                    "success": False,
                    "can_start_attempt2": False,
                    "message": "NOT_YET_READY",
                }

    assignment.seminar_confirmed = True
    assignment.seminar_confirmed_at = _utc_now()

    await db.commit()

    return {
        "success": True,
        "can_start_attempt2": True,
        "message": "Seminar confirmed. You can start attempt 2.",
    }
