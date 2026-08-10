#!/bin/bash
# eco-chat.uz — SAFE PostgreSQL Restore Script
# Faqat TARGET database'ga restore qiladi, production DB'ni emas.
# 
# MUHIM: Bu script production DB'ni emas, backup'ni restore qiladi.
# Production DB'ga restore qilish uchun alohida manualdan o'ting.
#
# Usage: ./restore.sh <backup_file.dump.gz> [restore_db_name]
# Default restore_db_name: ecochat_restore_<timestamp>  (production'ga emas!)
#
# QOIDA: Production DB'ga restore = manual jarayon, avtomatik emas.

set -euo pipefail

BACKUP_FILE="${1:-}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
# Default: ALOHIDA restore database (production'ga emas!)
TARGET_DB="${2:-ecochat_restore_${TIMESTAMP}}"
DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-ecochat}"
DB_PASS="${POSTGRES_PASSWORD:-ecochat_pass}"
PROD_DB="${POSTGRES_DB:-ecochat_db}"
LOG_FILE="/backups/eco-chat/restore_${TIMESTAMP}.log"
mkdir -p /backups/eco-chat

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "==========================================="
log "ECO-CHAT SAFE RESTORE OPERATION"
log "Backup: $BACKUP_FILE"
log "Target: $TARGET_DB @ $DB_HOST:$DB_PORT"
log "PROD DB (protected): $PROD_DB"
log "==========================================="

# ── Input validation ────────────────────────────────────────
if [[ -z "$BACKUP_FILE" ]]; then
    echo "Usage: $0 <backup_file.dump.gz> [restore_db_name]"
    echo ""
    echo "Available backups:"
    ls -lh /backups/eco-chat/eco_chat_*.dump.gz 2>/dev/null || echo "  (none found)"
    exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    log "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# ── CRITICAL SAFETY GUARD ────────────────────────────────────
# Restore target production DB'ga mos kelsa — BLOKLASH
if [[ "$TARGET_DB" == "$PROD_DB" ]]; then
    log "==========================================="
    log "SAFETY GUARD: RESTORE TO PRODUCTION DB BLOCKED!"
    log "==========================================="
    log "Target '$TARGET_DB' is the PRODUCTION database."
    log ""
    log "To restore to production, follow the manual procedure:"
    log "  1. Stop the application"
    log "  2. Create a fresh backup of current production"
    log "  3. Manually run this script with explicit prod flag"
    log ""
    log "If you REALLY need to restore to production:"
    log "  ALLOW_PROD_RESTORE=YES ./restore.sh <file> $PROD_DB"
    log "==========================================="
    exit 1
fi

# Allow production restore only with explicit flag
if [[ "$TARGET_DB" == "$PROD_DB" ]] && [[ "${ALLOW_PROD_RESTORE:-NO}" != "YES" ]]; then
    log "ERROR: Production restore requires ALLOW_PROD_RESTORE=YES"
    exit 1
fi

export PGPASSWORD="$DB_PASS"

# ── Decompress backup ────────────────────────────────────────
TEMP_FILE="/tmp/eco_restore_${TIMESTAMP}.dump"
log "Decompressing backup..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" > "$TEMP_FILE"
else
    cp "$BACKUP_FILE" "$TEMP_FILE"
fi
log "Decompressed: $TEMP_FILE ($(du -h "$TEMP_FILE" | cut -f1))"

# ── Validate backup file ─────────────────────────────────────
log "Validating backup file format..."
if ! pg_restore --list "$TEMP_FILE" > /dev/null 2>&1; then
    log "ERROR: Backup file is not a valid PostgreSQL dump!"
    rm -f "$TEMP_FILE"
    exit 1
fi
log "Backup file format: VALID"

# ── Create restore database ──────────────────────────────────
log "Creating restore target database: $TARGET_DB"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres \
    -c "DROP DATABASE IF EXISTS $TARGET_DB;" >> "$LOG_FILE" 2>&1
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres \
    -c "CREATE DATABASE $TARGET_DB OWNER $DB_USER;" >> "$LOG_FILE" 2>&1
log "Restore database created: $TARGET_DB"

# ── Restore ──────────────────────────────────────────────────
log "Restoring data to $TARGET_DB..."
if pg_restore \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$TARGET_DB" \
    --no-owner \
    --no-privileges \
    "$TEMP_FILE" >> "$LOG_FILE" 2>&1; then
    log "Restore: SUCCESS"
else
    log "Restore: completed with warnings (check log)"
fi

# ── Row count verification ───────────────────────────────────
log ""
log "=== RESTORED DATA VERIFICATION ==="
TABLES="admins branches employees topics questions question_answers employee_topic_assignments employee_topic_questions test_attempts attempt_questions audit_logs"

TOTAL_ROWS=0
for TABLE in $TABLES; do
    COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TARGET_DB" \
        -t -c "SELECT COUNT(*) FROM $TABLE;" 2>/dev/null | tr -d ' ' || echo "ERROR")
    log "  $TABLE: $COUNT rows"
    if [[ "$COUNT" =~ ^[0-9]+$ ]]; then
        TOTAL_ROWS=$((TOTAL_ROWS + COUNT))
    fi
done
log "  TOTAL ROWS: $TOTAL_ROWS"

# ── Compare with production (if accessible) ──────────────────
log ""
log "=== COMPARING WITH PRODUCTION ($PROD_DB) ==="
for TABLE in employees topics questions test_attempts; do
    PROD_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$PROD_DB" \
        -t -c "SELECT COUNT(*) FROM $TABLE;" 2>/dev/null | tr -d ' ' || echo "N/A")
    REST_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TARGET_DB" \
        -t -c "SELECT COUNT(*) FROM $TABLE;" 2>/dev/null | tr -d ' ' || echo "N/A")
    
    if [[ "$PROD_COUNT" == "$REST_COUNT" ]]; then
        log "  [MATCH] $TABLE: prod=$PROD_COUNT restore=$REST_COUNT"
    else
        log "  [DIFF]  $TABLE: prod=$PROD_COUNT restore=$REST_COUNT"
    fi
done

# ── Cleanup ──────────────────────────────────────────────────
rm -f "$TEMP_FILE"

log ""
log "==========================================="
log "RESTORE COMPLETE!"
log "Restored to: $TARGET_DB (NOT production!)"
log "Log: $LOG_FILE"
log ""
log "To promote to production:"
log "  1. Verify data in $TARGET_DB"
log "  2. Stop application"
log "  3. Manually switch connection string"
log "  4. Run: alembic upgrade head"
log "  5. Restart application"
log "==========================================="
