"""initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Base entities
    op.create_table('admins',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )
    
    op.create_table('branches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    op.create_table('topics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('short_name', sa.String(length=100), nullable=False),
        sa.Column('full_name', sa.String(length=500), nullable=False),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sequence_order')
    )
    op.create_index('ix_topic_order_active', 'topics', ['sequence_order', 'is_active'], unique=False)
    
    # 2. Level 1 dependencies
    op.create_table('employees',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('full_name', sa.String(length=300), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('registration_state', sa.String(length=30), nullable=True),
        sa.Column('registered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_user_id')
    )
    op.create_index('ix_emp_telegram', 'employees', ['telegram_user_id'], unique=False)
    op.create_index('ix_emp_branch', 'employees', ['branch_id'], unique=False)
    
    op.create_table('questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('ACTIVE', 'ARCHIVED')", name='check_question_status'),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_question_topic_status', 'questions', ['topic_id', 'status'], unique=False)
    
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('admin_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('old_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['admin_id'], ['admins.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_admin_action_date', 'audit_logs', ['admin_id', 'action', 'created_at'], unique=False)
    
    # 3. Level 2 dependencies
    op.create_table('question_answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('option_label', postgresql.CHAR(length=1), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.CheckConstraint("option_label IN ('A', 'B', 'C', 'D')", name='check_option_label'),
        sa.CheckConstraint("sort_order IN (1, 2, 3, 4)", name='check_sort_order'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_question_answer_correct', 'question_answers', ['question_id'], unique=True, postgresql_where=sa.text('is_correct = true'))
    
    # EmployeeTopicAssignment initially without attempt FKs (to break cycles if any, or just create it)
    op.create_table('employee_topic_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('attempt1_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('attempt2_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=True),
        sa.Column('seminar_confirmed', sa.Boolean(), nullable=True),
        sa.Column('seminar_confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'topic_id', name='uq_assign_emp_topic')
    )
    op.create_index('ix_assign_emp_topic', 'employee_topic_assignments', ['employee_id', 'topic_id'], unique=False)
    
    op.create_table('test_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assignment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('current_question_index', sa.Integer(), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint('attempt_number IN (1, 2)', name='check_attempt_number'),
        sa.CheckConstraint("status IN ('IN_PROGRESS', 'COMPLETED')", name='check_attempt_status'),
        sa.ForeignKeyConstraint(['assignment_id'], ['employee_topic_assignments.id'], ),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'topic_id', 'attempt_number', name='uq_attempt_emp_topic_num')
    )
    op.create_index('ix_attempt_emp_topic_status', 'test_attempts', ['employee_id', 'topic_id', 'status'], unique=False)
    
    # add cyclic FK to employee_topic_assignments
    op.create_foreign_key('fk_assign_attempt1', 'employee_topic_assignments', 'test_attempts', ['attempt1_id'], ['id'])
    op.create_foreign_key('fk_assign_attempt2', 'employee_topic_assignments', 'test_attempts', ['attempt2_id'], ['id'])
    
    op.create_table('employee_topic_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assignment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('base_slot', sa.Integer(), nullable=False),
        sa.Column('question_text_snapshot', sa.String(), nullable=False),
        sa.Column('answers_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('correct_answer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['assignment_id'], ['employee_topic_assignments.id'], ),
        sa.ForeignKeyConstraint(['correct_answer_id'], ['question_answers.id'], ),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assignment_id', 'base_slot', name='uq_assign_slot'),
        sa.UniqueConstraint('assignment_id', 'question_id', name='uq_assign_question')
    )
    
    op.create_table('attempt_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('attempt_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assignment_question_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column('answer_display_order', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('question_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('question_deadline_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('answered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('selected_answer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('answer_status', sa.String(length=20), nullable=True),
        sa.CheckConstraint("answer_status IN ('PENDING', 'ANSWERED', 'TIMEOUT')", name='check_answer_status'),
        sa.ForeignKeyConstraint(['assignment_question_id'], ['employee_topic_questions.id'], ),
        sa.ForeignKeyConstraint(['attempt_id'], ['test_attempts.id'], ),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
        sa.ForeignKeyConstraint(['selected_answer_id'], ['question_answers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('attempt_id', 'assignment_question_id', name='uq_attempt_assign_q'),
        sa.UniqueConstraint('attempt_id', 'display_order', name='uq_attempt_order')
    )
    op.create_index('ix_attempt_q_status', 'attempt_questions', ['attempt_id', 'answer_status'], unique=False)


def downgrade() -> None:
    op.drop_table('attempt_questions')
    op.drop_table('employee_topic_questions')
    op.drop_constraint('fk_assign_attempt2', 'employee_topic_assignments', type_='foreignkey')
    op.drop_constraint('fk_assign_attempt1', 'employee_topic_assignments', type_='foreignkey')
    op.drop_table('test_attempts')
    op.drop_table('employee_topic_assignments')
    op.drop_table('question_answers')
    op.drop_table('audit_logs')
    op.drop_table('questions')
    op.drop_table('employees')
    op.drop_table('topics')
    op.drop_table('branches')
    op.drop_table('admins')
