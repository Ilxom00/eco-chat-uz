#!/bin/bash
# eco-chat.uz PostgreSQL Backup Script
# Usage: ./backup.sh [backup_dir]
# Cron: 0 2 * * * /path/to/backup.sh >> /var/log/eco-backup.log 2>&1

set -euo pipefail

BACKUP_DIR="${1:-/backups/eco-chat}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-ecochat_db}"
DB_USER="${POSTGRES_USER:-ecochat}"
DB_PASS="${POSTGRES_PASSWORD:-ecochat_pass}"
LOG_FILE="${BACKUP_DIR}/backup.log"
BACKUP_FILE="${BACKUP_DIR}/eco_chat_${TIMESTAMP}.dump"
VERIFY_FILE="${BACKUP_DIR}/eco_chat_${TIMESTAMP}.verify"

# ── Setup ───────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "═══════════════════════════════════════════"
log "Starting ECO-CHAT backup: $TIMESTAMP"
log "Database: $DB_NAME @ $DB_HOST:$DB_PORT"
log "Output: $BACKUP_FILE"

# ── Create backup ─────────────────────────────────────────
export PGPASSWORD="$DB_PASS"

log "Running pg_dump..."
if pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -Fc \
    --verbose \
    -f "$BACKUP_FILE" 2>>"$LOG_FILE"; then
    
    BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
    log "✅ Backup created successfully. Size: $BACKUP_SIZE"
else
    log "❌ BACKUP FAILED!"
    exit 1
fi

# ── Verify backup ─────────────────────────────────────────
log "Verifying backup integrity..."
if pg_restore --list "$BACKUP_FILE" > "$VERIFY_FILE" 2>>"$LOG_FILE"; then
    OBJECT_COUNT=$(wc -l < "$VERIFY_FILE")
    log "✅ Backup verified. Objects: $OBJECT_COUNT"
    rm "$VERIFY_FILE"
else
    log "❌ BACKUP VERIFICATION FAILED!"
    exit 1
fi

# ── Compress ────────────────────────────────────────────────
log "Compressing backup..."
gzip "$BACKUP_FILE"
FINAL_FILE="${BACKUP_FILE}.gz"
FINAL_SIZE=$(du -sh "$FINAL_FILE" | cut -f1)
log "✅ Compressed: $FINAL_SIZE → $FINAL_FILE"

# ── Clean old backups ──────────────────────────────────────
log "Cleaning backups older than ${RETENTION_DAYS} days..."
DELETED=$(find "$BACKUP_DIR" -name "eco_chat_*.dump.gz" -mtime "+${RETENTION_DAYS}" -delete -print | wc -l)
log "Deleted $DELETED old backup(s)"

# ── Summary ───────────────────────────────────────────────
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "eco_chat_*.dump.gz" | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "Backup complete. Total: $TOTAL_BACKUPS backups, $TOTAL_SIZE disk"
log "═══════════════════════════════════════════"

exit 0
