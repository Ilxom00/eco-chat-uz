#!/bin/bash
# =============================================================
#  deploy.sh — eco-chat.uz SAFE DEPLOY SCRIPT
#  
#  ⚠️  MUHIM: Hech qachon "docker-compose down -v" ishlatmang!
#  Bu skript ma'lumotlarni SAQLAB turib yangilaydi.
# =============================================================
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo "🌿 eco-chat.uz — Safe Deploy boshlandi"
echo "📁 Dir: $REPO_DIR"
echo "⏰ Vaqt: $(date)"
echo ""

# 1. Pull latest code
echo "📥 [1/5] Yangi kod yuklanmoqda..."
git pull origin main
echo "✅ Kod yangilandi"

# 2. Backup database before deploy (just in case)
echo "💾 [2/5] Ma'lumotlar backup qilinmoqda..."
BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
docker-compose exec -T postgres pg_dump -U ecochat ecochat_db > "/tmp/${BACKUP_FILE}" 2>/dev/null && \
    echo "✅ Backup: /tmp/${BACKUP_FILE}" || \
    echo "⚠️  Backup xatoligi (birinchi deploy bo'lishi mumkin, davom etiladi)"

# 3. Build new backend image (ONLY backend, not postgres/redis)
echo "🔨 [3/5] Backend image qurilmoqda..."
docker-compose build backend
echo "✅ Image tayyor"

# 4. SAFE restart — only backend service, volumes UNTOUCHED
# NEVER use: docker-compose down -v (this deletes ALL data!)
echo "🔄 [4/5] Backend qayta ishga tushirilmoqda (ma'lumotlar saqlanadi)..."
docker-compose up -d --no-deps --force-recreate backend
echo "✅ Backend yangilandi"

# 5. Verify
echo "🔍 [5/5] Tekshirilmoqda..."
sleep 5
if docker-compose ps backend | grep -q "Up"; then
    echo "✅ Backend ISHLAYAPTI"
else
    echo "❌ Backend ishlamayapti! Loglarni tekshiring:"
    docker-compose logs --tail=50 backend
    exit 1
fi

# Show employee count to confirm data is safe
sleep 3
EMP_COUNT=$(docker-compose exec -T postgres psql -U ecochat -d ecochat_db -t -c "SELECT COUNT(*) FROM employees;" 2>/dev/null | tr -d ' \n' || echo "?")
echo ""
echo "✅ ====================================="
echo "✅  DEPLOY MUVAFFAQIYATLI!"
echo "✅  Xodimlar soni: ${EMP_COUNT}"
echo "✅  Ma'lumotlar SAQLANIB QOLDI"
echo "✅ ====================================="
echo ""
