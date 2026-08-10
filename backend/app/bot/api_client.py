import httpx
from typing import Optional

# Using placeholder for settings import, expecting app.config to exist
try:
    from app.config import settings
except ImportError:
    class Settings:
        backend_url = "http://localhost:8000"
        internal_api_secret = "secret"
    settings = Settings()

class BotAPIClient:
    def __init__(self):
        self.base_url = settings.backend_url
        self.headers = {'X-Internal-Secret': settings.internal_api_secret}
        self.timeout = httpx.Timeout(10.0)

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}/internal/bot{endpoint}"
            try:
                response = await client.request(method, url, headers=self.headers, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"API Error: {e}")
                raise e

    async def register_employee(self, telegram_user_id: int, full_name: str, branch_id: str, phone: str, branch_name: str = None) -> dict:
        return await self._request("POST", "/register", json={
            "telegram_user_id": telegram_user_id,
            "full_name": full_name,
            "branch_id": branch_id,
            "branch_name": branch_name,
            "phone": phone
        })

    async def get_employee_status(self, telegram_user_id: int) -> dict:
        return await self._request("GET", f"/employee/{telegram_user_id}/status")

    async def get_branches(self) -> list:
        return await self._request("GET", "/branches")

    async def get_topics(self, telegram_user_id: int) -> list:
        return await self._request("GET", f"/employee/{telegram_user_id}/topics")
        
    async def get_topic(self, topic_id: str) -> dict:
        return await self._request("GET", f"/topics/{topic_id}")

    async def start_attempt(self, telegram_user_id: int, topic_id: int, attempt_number: int, seminar_confirmed: bool = False) -> dict:
        return await self._request("POST", "/attempt/start", json={
            "telegram_user_id": telegram_user_id,
            "topic_id": topic_id,
            "attempt_number": attempt_number,
            "seminar_confirmed": seminar_confirmed
        })

    async def get_current_question(self, attempt_id: int) -> dict:
        return await self._request("GET", f"/attempt/{attempt_id}/question")

    async def submit_answer(self, attempt_id: int, display_order: int, selected_answer_id: int) -> dict:
        return await self._request("POST", f"/attempt/{attempt_id}/answer", json={
            "display_order": display_order,
            "selected_answer_id": selected_answer_id
        })

    async def get_attempt_results(self, attempt_id: int) -> dict:
        return await self._request("GET", f"/attempt/{attempt_id}/results")

    async def confirm_seminar(self, attempt_id: int) -> dict:
        return await self._request("POST", f"/attempt2/confirm-seminar", json={
            "attempt_id": attempt_id
        })

bot_api = BotAPIClient()
