"""
eco-chat.uz — Bot Connection Test Script
Telegram API ga ulanishni va bot ma'lumotlarini tekshiradi.
Docker talab qilmaydi.
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_bot_connection():
    print("=" * 50)
    print("eco-chat.uz — Telegram Bot Ulanish Testi")
    print("=" * 50)

    # Load token from .env
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    token = None

    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break

    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN .env faylda topilmadi!")
        return False

    print(f"Token: {token[:10]}...{token[-5:]}")

    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://api.telegram.org/bot{token}/getMe"
            )
            data = resp.json()

            if data.get("ok"):
                bot = data["result"]
                print(f"\nBOT MA'LUMOTLARI:")
                print(f"  Nomi    : {bot['first_name']}")
                print(f"  Username: @{bot.get('username', 'N/A')}")
                print(f"  ID      : {bot['id']}")
                print(f"\nUlanish: MUVAFFAQIYATLI!")
                return True
            else:
                print(f"Xato: {data}")
                return False

    except ImportError:
        print("httpx o'rnatilmagan. pip install httpx")
        return False
    except Exception as e:
        print(f"Ulanish xatosi: {e}")
        return False


async def test_webhook_clear():
    """Clear any existing webhook so polling works."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    token = None

    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break

    if not token:
        return

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            # Delete webhook so polling mode works
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/deleteWebhook",
                json={"drop_pending_updates": True}
            )
            result = resp.json()
            if result.get("ok"):
                print("  Webhook: tozalandi (polling rejimi uchun)")
            else:
                print(f"  Webhook tozalash: {result}")
    except Exception as e:
        print(f"  Webhook xatosi: {e}")


if __name__ == "__main__":
    async def main():
        success = await test_bot_connection()
        if success:
            print("\nWebhook tozalanmoqda...")
            await test_webhook_clear()
            print("\nBot ishga tayyor!")
            print("Docker bilan ishga tushirish uchun:")
            print("  docker-compose up -d")
        else:
            print("\nToken yoki internet ulanishini tekshiring.")
            sys.exit(1)

    asyncio.run(main())
