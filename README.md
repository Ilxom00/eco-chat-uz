# 🌿 eco-chat.uz

**Davlat Ekologik Ekspertizasi Markazi**  
Xodimlar bilim darajasini o'lchash tizimi

---

## Tizim haqida

- **Web Admin Panel** — bilim natijalarini real-vaqt kuzatish
- **Telegram Bot** — [@Eco234_bot](https://t.me/Eco234_bot) — xodimlar uchun test
- **48 ta avtomatik test** — barcha biznes qoidalar tekshirilgan

---

## Tez ishga tushirish

### Talablar
- Docker Desktop (Windows/Mac/Linux)
- Internet ulanishi

### 1. Loyihani yuklab oling
```bash
git clone <repo-url>
cd eco-chat
```

### 2. .env faylini sozlang
```bash
copy .env.example .env
```

`.env` faylini oching va quyidagilarni to'ldiring:

| O'zgaruvchi | Tavsif |
|-------------|--------|
| `TELEGRAM_BOT_TOKEN` | BotFather dan olingan token ✅ (tayyor) |
| `SECRET_KEY` | JWT uchun uzun tasodifiy kalit |
| `ADMIN_SECRET` | Super admin yaratish kodi |
| `INTERNAL_API_SECRET` | Bot ↔ API maxfiy kalit |
| `POSTGRES_PASSWORD` | PostgreSQL paroli |

### 3. Docker bilan ishga tushiring
```bash
docker-compose up -d
```

### 4. Super Admin yarating
```bash
docker-compose exec backend python scripts/create_superadmin.py
```

### 5. Tekshiring
```bash
# Health check
curl http://localhost/health

# Web admin panel
# http://localhost

# Telegram bot
# https://t.me/Eco234_bot → /start
```

---

## Loyiha tuzilishi

```
eco-chat/
├── docker-compose.yml         # Barcha xizmatlar
├── .env                       # Mahalliy sozlamalar (git'ga kirmaydi!)
├── .env.example               # Shablon
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py            # FastAPI + bot startup
│   │   ├── config.py          # Barcha sozlamalar
│   │   ├── models/            # SQLAlchemy modellari
│   │   ├── services/
│   │   │   └── test_engine.py ← ASOSIY BIZNES LOGIKA
│   │   ├── api/               # REST API endpointlari
│   │   ├── bot/               # Telegram Bot handlerlari
│   │   └── utils/             # Security, timer, validators
│   ├── alembic/               # DB migratsiyalari
│   ├── tests/                 # 48 ta avtomatik test
│   └── scripts/               # backup.sh, restore.sh
│
└── frontend/                  # Web Admin SPA
    ├── login.html
    ├── index.html
    ├── css/                   # Enterprise yashil dizayn
    └── js/                    # Modular JavaScript
```

---

## Asosiy qoidalar (business invariants)

| # | Qoida | Qayerda |
|---|-------|---------|
| 1 | Mavzular ketma-ketlikda ochiladi | `can_start_attempt()` |
| 2 | 1-mavzu: Ikkala urinish tugamaguncha 2-mavzu yopiq | `EmployeeTopicAssignment.status` |
| 3 | Max 2 urinish (DB UNIQUE constraint) | `test_attempts` |
| 4 | 15 ta random savol bir marta tanlanadi | `get_or_create_assignment()` |
| 5 | 2-urinishda aynan o'sha 15 savol | `EmployeeTopicQuestion` (immutable) |
| 6 | Savol/javob tartibi aralashtiriladi, farqli bo'ladi | `_shuffle_different()` |
| 7 | 30 sek timer PostgreSQL'da saqlanadi | `question_deadline_at` |
| 8 | Telegram yopish timerni reset qilmaydi | RAM'da emas, DB'da |
| 9 | 10 daqiqa + seminar tasdiqi | `attempt2_min_wait_seconds` |
| 10 | Web=API=Bot=Excel — bir hisob | `result_service.py` SSoT |

---

## Rivojlantirish

### Testlarni ishga tushirish
```bash
cd backend
python -m pytest tests/test_critical.py -v
# 48 passed ✅
```

### Botni test qilish
```bash
python test_bot_connection.py
```

### Ma'lumotlar bazasi
```bash
# Migratsiya
docker-compose exec backend alembic upgrade head

# Backup
docker-compose exec postgres sh /backup.sh
```

---

## Xavfsizlik

- ✅ Token hech qachon kodda yoki git'da emas
- ✅ JWT HttpOnly cookie (XSS himoya)
- ✅ Telegram telefon spoof himoyasi
- ✅ SQL injection: SQLAlchemy ORM
- ✅ Race condition: SELECT FOR UPDATE + Redis idempotency
- ✅ Har kecha avtomatik backup

---

*eco-chat.uz — Production-Ready Enterprise Knowledge Assessment System*
