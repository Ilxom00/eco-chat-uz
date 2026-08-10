import os
import textwrap

BASE_DIR = r"c:\Users\user\.gemini\antigravity\scratch\EcoTest"

def write_file(path, content):
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')
    print(f"Created {path}")

FILES = {}

FILES["docker-compose.yml"] = """
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ecochat
      POSTGRES_PASSWORD: ecochat_pass
      POSTGRES_DB: ecochat_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ecochat -d ecochat_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - ecochat-network

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - ecochat-network

  backend:
    build: 
      context: ./backend
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - ecochat-network

  frontend:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./frontend/www:/usr/share/nginx/html:ro
    depends_on:
      - backend
    networks:
      - ecochat-network

volumes:
  postgres_data:
  redis_data:

networks:
  ecochat-network:
    driver: bridge
"""

FILES[".env.example"] = """
DATABASE_URL=postgresql+asyncpg://ecochat:ecochat_pass@postgres:5432/ecochat_db
DATABASE_URL_SYNC=postgresql://ecochat:ecochat_pass@postgres:5432/ecochat_db
REDIS_URL=redis://redis:6379/0
TELEGRAM_BOT_TOKEN=
SECRET_KEY=change-this-to-a-very-long-random-secret-key-in-production
ADMIN_SECRET=change-this-admin-bootstrap-secret
ENVIRONMENT=development
LOG_LEVEL=INFO
CORSORIGINS=["http://localhost","http://localhost:80","http://localhost:3000"]
BACKUP_DIR=/backups
TZ=Asia/Tashkent
INTERNAL_API_SECRET=change-this-internal-bot-api-secret
"""

FILES["backend/Dockerfile"] = """
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run migrations and start app
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

FILES["backend/requirements.txt"] = """
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy[asyncio]>=2.0.25
asyncpg>=0.29.0
psycopg2-binary>=2.9.9
alembic>=1.13.1
pydantic>=2.5.3
pydantic-settings>=2.1.0
python-multipart>=0.0.6
bcrypt>=4.1.2
pyjwt>=2.8.0
redis>=5.0.1
aioredis>=2.0.1
httpx>=0.26.0
openpyxl>=3.1.2
python-telegram-bot>=20.7
apscheduler>=3.10.4
loguru>=0.7.2
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
"""

FILES["backend/app/config.py"] = """
from pydantic_settings import BaseSettings
from typing import List
import json

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://ecochat:ecochat_pass@localhost:5432/ecochat_db"
    database_url_sync: str = "postgresql://ecochat:ecochat_pass@localhost:5432/ecochat_db"
    redis_url: str = "redis://localhost:6379/0"
    telegram_bot_token: str = ""
    secret_key: str = "secret"
    admin_secret: str = "admin-secret"
    internal_api_secret: str = "internal-secret"
    environment: str = "development"
    log_level: str = "INFO"
    corsorigins: str = '["*"]'
    tz: str = "Asia/Tashkent"
    
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    
    question_timer_seconds: int = 30
    min_questions_per_topic: int = 15
    attempt2_min_wait_seconds: int = 600
    max_attempts_per_topic: int = 2

    class Config:
        env_file = ".env"

    @property
    def cors_origins_list(self) -> List[str]:
        try:
            return json.loads(self.corsorigins)
        except:
            return ["*"]

settings = Settings()
"""

FILES["backend/app/database.py"] = """
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.config import settings

engine = create_async_engine(settings.database_url, echo=(settings.environment == "development"))
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
"""

FILES["backend/app/redis_client.py"] = """
import redis.asyncio as redis
from app.config import settings

redis_pool = redis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)

def get_redis():
    return redis.Redis(connection_pool=redis_pool)
"""

FILES["backend/app/main.py"] = """
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.redis_client import get_redis
from app.database import get_db, engine
from sqlalchemy import text
from loguru import logger
import datetime
import pytz

app = FastAPI(title="Eco-Chat API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")
    await engine.dispose()

@app.get("/health")
async def health_check(db = Depends(get_db)):
    status = {"status": "ok", "timestamp": datetime.datetime.now(pytz.timezone(settings.tz)).isoformat()}
    try:
        await db.execute(text("SELECT 1"))
        status["db"] = "ok"
    except Exception as e:
        status["db"] = f"error: {str(e)}"
        
    try:
        redis = get_redis()
        await redis.ping()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = f"error: {str(e)}"
        
    return status
"""

FILES["backend/app/utils/security.py"] = """
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
import uuid
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return {}

def generate_uuid() -> str:
    return str(uuid.uuid4())
"""

FILES["backend/app/utils/validators.py"] = """
import re

def validate_phone(phone: str) -> str:
    cleaned = re.sub(r'\\D', '', phone)
    if len(cleaned) == 9:
        return f"+998{cleaned}"
    elif len(cleaned) == 12 and cleaned.startswith("998"):
        return f"+{cleaned}"
    raise ValueError("Invalid phone format")

def validate_full_name(name: str) -> bool:
    if not name or len(name.strip()) < 3:
        return False
    if name.strip().isdigit():
        return False
    return True
"""

FILES["backend/app/utils/timer.py"] = """
from datetime import datetime, timedelta
import pytz

def get_utc_now() -> datetime:
    return datetime.utcnow().replace(tzinfo=pytz.utc)

def compute_deadline(started_at: datetime, seconds: int = 30) -> datetime:
    return started_at + timedelta(seconds=seconds)

def is_expired(deadline_at: datetime) -> bool:
    return get_utc_now() > deadline_at

def remaining_seconds(deadline_at: datetime) -> int:
    delta = deadline_at - get_utc_now()
    return max(0, int(delta.total_seconds()))
"""

FILES["backend/alembic.ini"] = """
[alembic]
script_location = alembic
sqlalchemy.url = postgresql://ecochat:ecochat_pass@localhost:5432/ecochat_db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""

FILES["backend/alembic/env.py"] = """
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.models.base import Base
from app.models import *  # Import all models

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
"""

FILES["backend/scripts/create_superadmin.py"] = """
import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.admin import Admin
from app.utils.security import get_password_hash
from sqlalchemy.future import select

async def create_superadmin():
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    fullname = os.getenv("ADMIN_FULLNAME", "Super Administrator")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Admin).filter_by(username=username))
        admin = result.scalar_one_or_none()
        
        if not admin:
            new_admin = Admin(
                username=username,
                password_hash=get_password_hash(password),
                full_name=fullname,
                is_active=True
            )
            session.add(new_admin)
            await session.commit()
            print(f"Superadmin {username} created.")
        else:
            print(f"Superadmin {username} already exists.")

if __name__ == "__main__":
    asyncio.run(create_superadmin())
"""

FILES["frontend/nginx.conf"] = """
server {
    listen 80;
    server_name localhost;

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /internal/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
"""

FILES["README.md"] = """
# Eco-Chat.uz Enterprise System

## Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)

## Quick Start
1. Copy `.env.example` to `.env` and fill in your values.
2. Run `docker-compose up -d --build`
3. Access API at `http://localhost:8000`
4. Create superadmin: `docker-compose exec backend python scripts/create_superadmin.py`

## Development
- API documentation available at `/docs`
- Use Alembic for migrations: `alembic revision --autogenerate -m "msg"`, `alembic upgrade head`
"""

# Phase 2 Models
FILES["backend/app/models/__init__.py"] = """
from .base import Base
from .admin import Admin
from .branch import Branch
from .employee import Employee
from .topic import Topic
from .question import Question, QuestionAnswer
from .attempt import EmployeeTopicAssignment, EmployeeTopicQuestion, TestAttempt, AttemptQuestion
from .audit import AuditLog
"""

FILES["backend/app/models/base.py"] = """
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
"""

FILES["backend/app/models/admin.py"] = """
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from .base import BaseModel

class Admin(BaseModel):
    __tablename__ = 'admins'
    
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200))
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
"""

FILES["backend/app/models/branch.py"] = """
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.sql import func
from .base import BaseModel

class Branch(BaseModel):
    __tablename__ = 'branches'
    
    name = Column(String(200), unique=True, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
"""

FILES["backend/app/models/employee.py"] = """
from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import BaseModel

class Employee(BaseModel):
    __tablename__ = 'employees'
    
    telegram_user_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String(300), nullable=False)
    phone = Column(String(20), nullable=True)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.id'), nullable=True)
    registration_state = Column(String(30), default='PENDING')
    registered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_emp_telegram', 'telegram_user_id'),
        Index('ix_emp_branch', 'branch_id'),
    )
"""

FILES["backend/app/models/topic.py"] = """
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Index
from sqlalchemy.sql import func
from .base import BaseModel

class Topic(BaseModel):
    __tablename__ = 'topics'
    
    short_name = Column(String(100), nullable=False)
    full_name = Column(String(500), nullable=False)
    sequence_order = Column(Integer, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_topic_order_active', 'sequence_order', 'is_active'),
    )
"""

FILES["backend/app/models/question.py"] = """
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, CHAR
from sqlalchemy.sql import func
from .base import BaseModel

class Question(BaseModel):
    __tablename__ = 'questions'
    
    topic_id = Column(UUID(as_uuid=True), ForeignKey('topics.id'), nullable=False)
    text = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default='ACTIVE')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    archived_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        CheckConstraint(status.in_(['ACTIVE', 'ARCHIVED']), name='check_question_status'),
        Index('ix_question_topic_status', 'topic_id', 'status'),
    )

class QuestionAnswer(BaseModel):
    __tablename__ = 'question_answers'
    
    question_id = Column(UUID(as_uuid=True), ForeignKey('questions.id'), nullable=False)
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)
    option_label = Column(CHAR(1), nullable=False)
    sort_order = Column(Integer, nullable=False)
    
    __table_args__ = (
        CheckConstraint(option_label.in_(['A', 'B', 'C', 'D']), name='check_option_label'),
        CheckConstraint(sort_order.in_([1, 2, 3, 4]), name='check_sort_order'),
        Index('ix_question_answer_correct', 'question_id', unique=True, postgresql_where=(is_correct == True)),
    )
"""

FILES["backend/app/models/attempt.py"] = """
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from .base import BaseModel

class TestAttempt(BaseModel):
    __tablename__ = 'test_attempts'
    
    employee_id = Column(UUID(as_uuid=True), ForeignKey('employees.id'), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey('topics.id'), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey('employee_topic_assignments.id'), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default='IN_PROGRESS')
    current_question_index = Column(Integer, default=0)
    score = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('employee_id', 'topic_id', 'attempt_number', name='uq_attempt_emp_topic_num'),
        CheckConstraint(attempt_number.in_([1, 2]), name='check_attempt_number'),
        CheckConstraint(status.in_(['IN_PROGRESS', 'COMPLETED']), name='check_attempt_status'),
        Index('ix_attempt_emp_topic_status', 'employee_id', 'topic_id', 'status'),
    )

class EmployeeTopicAssignment(BaseModel):
    __tablename__ = 'employee_topic_assignments'
    
    employee_id = Column(UUID(as_uuid=True), ForeignKey('employees.id'), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey('topics.id'), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    attempt1_id = Column(UUID(as_uuid=True), ForeignKey('test_attempts.id', use_alter=True), nullable=True)
    attempt2_id = Column(UUID(as_uuid=True), ForeignKey('test_attempts.id', use_alter=True), nullable=True)
    status = Column(String(30), default='ASSIGNED')
    seminar_confirmed = Column(Boolean, default=False)
    seminar_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        UniqueConstraint('employee_id', 'topic_id', name='uq_assign_emp_topic'),
        Index('ix_assign_emp_topic', 'employee_id', 'topic_id'),
    )

class EmployeeTopicQuestion(BaseModel):
    __tablename__ = 'employee_topic_questions'
    
    assignment_id = Column(UUID(as_uuid=True), ForeignKey('employee_topic_assignments.id'), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey('questions.id'), nullable=False)
    base_slot = Column(Integer, nullable=False)
    question_text_snapshot = Column(String, nullable=False)
    answers_snapshot = Column(JSONB, nullable=False)
    correct_answer_id = Column(UUID(as_uuid=True), ForeignKey('question_answers.id'), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('assignment_id', 'question_id', name='uq_assign_question'),
        UniqueConstraint('assignment_id', 'base_slot', name='uq_assign_slot'),
    )

class AttemptQuestion(BaseModel):
    __tablename__ = 'attempt_questions'
    
    attempt_id = Column(UUID(as_uuid=True), ForeignKey('test_attempts.id'), nullable=False)
    assignment_question_id = Column(UUID(as_uuid=True), ForeignKey('employee_topic_questions.id'), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey('questions.id'), nullable=False)
    display_order = Column(Integer, nullable=False)
    answer_display_order = Column(JSONB, nullable=False)
    question_started_at = Column(DateTime(timezone=True), nullable=True)
    question_deadline_at = Column(DateTime(timezone=True), nullable=True)
    answered_at = Column(DateTime(timezone=True), nullable=True)
    selected_answer_id = Column(UUID(as_uuid=True), ForeignKey('question_answers.id'), nullable=True)
    is_correct = Column(Boolean, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    answer_status = Column(String(20), default='PENDING')
    
    __table_args__ = (
        UniqueConstraint('attempt_id', 'assignment_question_id', name='uq_attempt_assign_q'),
        UniqueConstraint('attempt_id', 'display_order', name='uq_attempt_order'),
        CheckConstraint(answer_status.in_(['PENDING', 'ANSWERED', 'TIMEOUT']), name='check_answer_status'),
        Index('ix_attempt_q_status', 'attempt_id', 'answer_status'),
    )
"""

FILES["backend/app/models/audit.py"] = """
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from .base import BaseModel

class AuditLog(BaseModel):
    __tablename__ = 'audit_logs'
    
    admin_id = Column(UUID(as_uuid=True), ForeignKey('admins.id'), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_audit_admin_action_date', 'admin_id', 'action', 'created_at'),
    )
"""

FILES["backend/alembic/versions/001_initial_schema.py"] = """
\"\"\"initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

\"\"\"
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
"""

for path, content in FILES.items():
    write_file(path, content)

print("All files created successfully!")
