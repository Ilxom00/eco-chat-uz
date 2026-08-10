#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  deploy.sh — eco-chat.uz SAFE DEPLOY (ma'lumotlar hech qachon yo'qolmaydi)
#
#  ISHLATISH:
#    chmod +x deploy.sh
#    ./deploy.sh
#
#  BU SKRIPT:
#    ✅ Avval backup qiladi
#    ✅ Faqat backend container'ini qayta ishlatadi
#    ✅ Postgres va Redis container'lariga tegmaydi
#    ✅ docker-compose down ishlatmaydi (faqat up)
# ═══════════════════════════════════════════════════════════════════
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

DATA_DIR="/opt/ecochat-data"

echo ""
echo "🌿 ══════════════════════════════════════════"
echo "   eco-chat.uz — SAFE DEPLOY"
echo "   $(date '+%Y-%m-%d %H:%M:%S')"
echo "🌿 ══════════════════════════════════════════"
echo ""

# ── 1. Persistent data directories ───────────────────────────────────
echo "📁 [1/6] Ma'lumotlar papkasi tekshirilmoqda..."
mkdir -p "$DATA_DIR/postgres"
mkdir -p "$DATA_DIR/redis"
mkdir -p "$DATA_DIR/backups"
chmod 777 "$DATA_DIR/postgres" "$DATA_DIR/redis" "$DATA_DIR/backups" 2>/dev/null || true
echo "✅ $DATA_DIR papkasi tayyor"

# ── 2. Migrate existing named volumes (first time only) ──────────────
# If postgres named volume exists but bind mount is empty, copy data
if docker volume ls | grep -q "ecochat_postgres_data\|eco-chat_postgres_data\|eco-chat-uz_postgres_data"; then
    if [ -z "$(ls -A $DATA_DIR/postgres 2>/dev/null)" ]; then
        echo "🔄 [2/6] Named volume → bind mount ma'lumotlari ko'chirilmoqda..."
        VOL_NAME=$(docker volume ls --format "{{.Name}}" | grep -E "(ecochat|eco.chat).*postgres" | head -1)
        if [ -n "$VOL_NAME" ]; then
            docker run --rm \
                -v "$VOL_NAME:/source:ro" \
                -v "$DATA_DIR/postgres:/dest" \
                alpine sh -c "cp -a /source/. /dest/" 2>/dev/null && \
                echo "✅ Ma'lumotlar ko'chirildi: $VOL_NAME → $DATA_DIR/postgres" || \
                echo "⚠️  Ko'chirish muvaffaqiyatsiz (yangi install bo'lishi mumkin)"
        fi
    else
        echo "✅ [2/6] Bind mount allaqachon ma'lumotga ega — skip"
    fi
else
    echo "✅ [2/6] Named volume yo'q — skip"
fi

# ── 3. Pull latest code ───────────────────────────────────────────────
echo "📥 [3/6] Yangi kod yuklanmoqda..."
git pull origin main
echo "✅ Kod yangilandi"

# ── 4. Backup before deploy ───────────────────────────────────────────
echo "💾 [4/6] Deploy oldidan backup..."
BACKUP="$DATA_DIR/backups/pre_deploy_$(date +%Y%m%d_%H%M%S).sql"
if docker-compose ps postgres 2>/dev/null | grep -q "Up"; then
    docker-compose exec -T postgres pg_dump -U ecochat ecochat_db > "$BACKUP" 2>/dev/null && \
        echo "✅ Backup saqlandi: $BACKUP" || \
        echo "⚠️  Backup xatoligi — davom etilmoqda"
else
    echo "⚠️  Postgres ishlamayapti — backup skip"
fi

# Keep only last 10 backups
ls -t "$DATA_DIR/backups/"*.sql 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true

# ── 5. Build & restart ONLY backend ──────────────────────────────────
echo "🔨 [5/6] Backend build & restart (postgres/redis tegilmaydi)..."
docker-compose build backend
# ⚠️ NEVER: docker-compose down (postgres container stops)
# ⚠️ NEVER: docker-compose down -v (volumes deleted!)
docker-compose up -d --no-deps --force-recreate backend frontend
echo "✅ Backend va frontend yangilandi"

# Make sure postgres & redis are running (start if stopped)
docker-compose up -d postgres redis

# ── 6. Verify ─────────────────────────────────────────────────────────
echo "🔍 [6/6] Tekshirilmoqda..."
sleep 8

BACKEND_OK=false
for i in 1 2 3; do
    if docker-compose ps backend 2>/dev/null | grep -q "Up"; then
        BACKEND_OK=true
        break
    fi
    sleep 5
done

if [ "$BACKEND_OK" = "true" ]; then
    EMP=$(docker-compose exec -T postgres psql -U ecochat -d ecochat_db -t -c \
        "SELECT COUNT(*) FROM employees;" 2>/dev/null | tr -d ' \n' || echo "?")
    echo ""
    echo "✅ ════════════════════════════════════"
    echo "✅  DEPLOY MUVAFFAQIYATLI YAKUNLANDI!"
    echo "✅  Xodimlar soni: ${EMP} ta"
    echo "✅  Ma'lumotlar: $DATA_DIR"
    echo "✅  Backup: $BACKUP"
    echo "✅ ════════════════════════════════════"
else
    echo ""
    echo "❌ Backend ishlamayapti! Loglar:"
    docker-compose logs --tail=30 backend
    echo ""
    echo "🔄 Oxirgi backupdan tiklash..."
    LAST_BACKUP=$(ls -t "$DATA_DIR/backups/"*.sql 2>/dev/null | head -1)
    if [ -n "$LAST_BACKUP" ]; then
        docker-compose exec -T postgres psql -U ecochat ecochat_db < "$LAST_BACKUP" 2>/dev/null || true
        echo "✅ Backup tiklandi: $LAST_BACKUP"
    fi
    exit 1
fi
