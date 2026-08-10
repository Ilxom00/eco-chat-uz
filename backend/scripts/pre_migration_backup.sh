#!/bin/bash
# eco-chat.uz — Pre-Migration Safety Script
# Migration dan OLDIN chaqirilishi shart.
# 1. Row counts oladi
# 2. Backup yaratadi
# 3. Backup validatsiya qiladi
# 4. Hisobot chiqaradi
#
# Usage: ./pre_migration_backup.sh
# Exit 0 = safe to proceed, Exit 1 = DO NOT MIGRATE

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-ecochat}"
DB_PASS="${POSTGRES_PASSWORD:-ecochat_pass}"
DB_NAME="${POSTGRES_DB:-ecochat_db}"
BACKUP_DIR="${BACKUP_DIR:-/backups}/eco-chat"
BACKUP_FILE="${BACKUP_DIR}/backup_before_migration_${TIMESTAMP}.dump.gz"
COUNTS_FILE="${BACKUP_DIR}/row_counts_before_migration_${TIMESTAMP}.json"
LOG_FILE="${BACKUP_DIR}/pre_migration_${TIMESTAMP}.log"

mkdir -p "$BACKUP_DIR"
export PGPASSWORD="$DB_PASS"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "==========================================="
log "ECO-CHAT PRE-MIGRATION SAFETY CHECK"
log "Database: $DB_NAME @ $DB_HOST:$DB_PORT"
log "Backup: $BACKUP_FILE"
log "==========================================="

# ── Step 1: Row Counts BEFORE migration ─────────────────────
log "Step 1: Recording row counts BEFORE migration..."

TABLES="admins branches employees topics questions question_answers employee_topic_assignments employee_topic_questions test_attempts attempt_questions audit_logs"

echo "{" > "$COUNTS_FILE"
echo "  \"timestamp\": \"$TIMESTAMP\"," >> "$COUNTS_FILE"
echo "  \"database\": \"$DB_NAME\"," >> "$COUNTS_FILE"
echo "  \"tables\": {" >> "$COUNTS_FILE"

FIRST=true
for TABLE in $TABLES; do
    COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -t -c "SELECT COUNT(*) FROM $TABLE;" 2>/dev/null | tr -d ' \n' || echo "-1")
    log "  $TABLE: $COUNT rows"
    
    if [[ "$FIRST" == "true" ]]; then
        FIRST=false
    else
        echo "," >> "$COUNTS_FILE"
    fi
    echo -n "    \"$TABLE\": $COUNT" >> "$COUNTS_FILE"
done

echo "" >> "$COUNTS_FILE"
echo "  }" >> "$COUNTS_FILE"
echo "}" >> "$COUNTS_FILE"

log "Row counts saved: $COUNTS_FILE"

# ── Step 2: Create Backup ────────────────────────────────────
log ""
log "Step 2: Creating backup..."

if ! pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=custom \
    --compress=9 \
    --verbose \
    -f "${BACKUP_FILE%.gz}" >> "$LOG_FILE" 2>&1; then
    log "ERROR: Backup FAILED!"
    log "MIGRATION ABORTED — backup must succeed before migrating."
    exit 1
fi

# Compress
gzip -9 "${BACKUP_FILE%.gz}"
log "Backup created: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# ── Step 3: Validate Backup ──────────────────────────────────
log ""
log "Step 3: Validating backup file..."

TEMP_DUMP="${BACKUP_FILE%.gz}.validate"
gunzip -c "$BACKUP_FILE" > "$TEMP_DUMP"

if pg_restore --list "$TEMP_DUMP" > /dev/null 2>&1; then
    log "Backup format: VALID"
else
    log "ERROR: Backup file is INVALID or CORRUPTED!"
    log "MIGRATION ABORTED — backup is not restorable."
    rm -f "$TEMP_DUMP"
    exit 1
fi

# Count tables in backup
TABLE_COUNT=$(pg_restore --list "$TEMP_DUMP" | grep -c "TABLE DATA" || echo "0")
log "Backup contains: $TABLE_COUNT table data sections"

rm -f "$TEMP_DUMP"

# ── Step 4: Restore Test to Temp DB ─────────────────────────
log ""
log "Step 4: Quick restore test (temp database)..."

TEST_DB="ecochat_backup_verify_${TIMESTAMP}"
TEMP_DUMP2="${BACKUP_FILE%.gz}.test"
gunzip -c "$BACKUP_FILE" > "$TEMP_DUMP2"

# Create test DB
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres \
    -c "DROP DATABASE IF EXISTS $TEST_DB;" >> "$LOG_FILE" 2>&1 || true
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres \
    -c "CREATE DATABASE $TEST_DB OWNER $DB_USER;" >> "$LOG_FILE" 2>&1

# Restore
RESTORE_OK=true
if ! pg_restore \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$TEST_DB" \
    --no-owner \
    --no-privileges \
    "$TEMP_DUMP2" >> "$LOG_FILE" 2>&1; then
    log "WARNING: Restore test had warnings (check log)"
fi

# Verify row counts match
log "Verifying restored data matches production..."
MISMATCH=false
for TABLE in $TABLES; do
    PROD_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -t -c "SELECT COUNT(*) FROM $TABLE;" 2>/dev/null | tr -d ' ' || echo "-1")
    REST_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB" \
        -t -c "SELECT COUNT(*) FROM $TABLE;" 2>/dev/null | tr -d ' ' || echo "-1")
    
    if [[ "$PROD_COUNT" == "$REST_COUNT" ]]; then
        log "  [MATCH] $TABLE: $PROD_COUNT rows"
    else
        log "  [FAIL]  $TABLE: prod=$PROD_COUNT restore=$REST_COUNT — MISMATCH!"
        MISMATCH=true
    fi
done

# Cleanup test DB
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres \
    -c "DROP DATABASE IF EXISTS $TEST_DB;" >> "$LOG_FILE" 2>&1 || true
rm -f "$TEMP_DUMP2"

if [[ "$MISMATCH" == "true" ]]; then
    log ""
    log "ERROR: Backup restore verification FAILED!"
    log "MIGRATION ABORTED — backup does not match production."
    exit 1
fi

log "Restore test: PASS"

# ── Summary ──────────────────────────────────────────────────
log ""
log "==========================================="
log "PRE-MIGRATION CHECK: ALL PASS"
log "==========================================="
log "  [PASS] BACKUP CREATED: $BACKUP_FILE"
log "  [PASS] BACKUP VALID"
log "  [PASS] RESTORE TEST"
log "  [PASS] ROW COUNTS SAVED: $COUNTS_FILE"
log ""
log "You may now proceed with migration:"
log "  alembic upgrade head"
log ""
log "If migration fails, restore from:"
log "  $BACKUP_FILE"
log "==========================================="

# Write machine-readable result
echo "{\"status\": \"SAFE_TO_MIGRATE\", \"backup\": \"$BACKUP_FILE\", \"counts\": \"$COUNTS_FILE\", \"timestamp\": \"$TIMESTAMP\"}"
exit 0
