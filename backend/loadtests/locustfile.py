# -*- coding: utf-8 -*-
import random
import uuid
from locust import HttpUser, task, between, SequentialTaskSet

# Internal secret token required for bot endpoints
INTERNAL_SECRET = "eco-internal-secret-2024-prod"

class EmployeeTestFlow(SequentialTaskSet):
    def on_start(self):
        # Generate synthetic telegram id and name
        self.tg_id = random.randint(990000000, 999999999)
        self.full_name = f"LOADTEST_EMP_{uuid.uuid4().hex[:8].upper()}"
        self.employee_id = None
        self.topic_id = None
        self.attempt_id = None
        
        # 10% of users will experience a timeout on some questions
        self.is_timeout_user = random.random() < 0.10

    @task
    def register_employee(self):
        headers = {"X-Internal-Secret": INTERNAL_SECRET}
        payload = {
            "telegram_user_id": self.tg_id,
            "full_name": self.full_name,
            "branch_name": "Давлат Экологик экспертизаси маркази (Марказий аппарат)",
            "phone": "+998991234567"
        }
        with self.client.post("/internal/bot/bot/register", json=payload, headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                res_data = response.json()
                if res_data.get("success") and res_data.get("employee_id"):
                    self.employee_id = res_data["employee_id"]
                    response.success()
                else:
                    response.failure(f"Registration succeeded but missing employee_id: {response.text}")
            else:
                response.failure(f"Registration HTTP error: {response.status_code} - {response.text}")

    @task
    def check_topic_availability(self):
        if not self.employee_id:
            self.interrupt()
            return
        headers = {"X-Internal-Secret": INTERNAL_SECRET}
        with self.client.get(f"/internal/bot/bot/employee/{self.tg_id}/topics", headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                topics = response.json()
                if len(topics) > 0:
                    # Select 1-Topic (sequence order 1)
                    self.topic_id = topics[0]["id"]
                    response.success()
                else:
                    response.failure("No active topics returned.")
            else:
                response.failure(f"Check topics failed: {response.status_code}")

    @task
    def start_attempt(self):
        if not self.topic_id:
            self.interrupt()
            return
        headers = {"X-Internal-Secret": INTERNAL_SECRET}
        payload = {
            "telegram_user_id": self.tg_id,
            "topic_id": self.topic_id,
            "attempt_number": 1
        }
        with self.client.post("/internal/bot/bot/attempt/start", json=payload, headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                res_data = response.json()
                if res_data.get("attempt_id"):
                    self.attempt_id = res_data["attempt_id"]
                    self.current_q = res_data.get("first_question")
                    response.success()
                else:
                    response.failure(f"Start attempt failed to return attempt_id: {response.text}")
            else:
                response.failure(f"Start attempt HTTP error: {response.status_code} - {response.text}")

    @task
    def answer_questions(self):
        if not self.attempt_id or not self.current_q:
            self.interrupt()
            return
        
        headers = {"X-Internal-Secret": INTERNAL_SECRET}
        
        # Loop for 15 questions
        for q_idx in range(1, 16):
            if not self.current_q:
                break
                
            aq_id = self.current_q.get("attempt_question_id")
            answers = self.current_q.get("answers", [])
            display_order = self.current_q.get("display_order", q_idx)
            
            # Select random answer
            ans_id = random.choice(answers)["id"] if answers else "dummy_ans"

            # 10% timeout cohort: timeout on question 5 and 10
            is_timeout = self.is_timeout_user and q_idx in [5, 10]
            
            if is_timeout:
                payload = {
                    "attempt_question_id": aq_id
                }
                url = f"/internal/bot/bot/attempt/{self.attempt_id}/timeout"
                name = "/internal/bot/bot/attempt/{attempt_id}/timeout"
            else:
                payload = {
                    "display_order": display_order,
                    "selected_answer_id": ans_id
                }
                url = f"/internal/bot/bot/attempt/{self.attempt_id}/answer"
                name = "/internal/bot/bot/attempt/{attempt_id}/answer"
                
            # Think-time
            # Normal: 2-10 seconds
            # Burst: 0.2-1.0 second (controlled by user properties, but we do random short sleep here)
            think_time = random.uniform(0.2, 1.0) if self.user.burst_mode else random.uniform(2.0, 5.0)
            self.user.wait_time = lambda: think_time
            
            with self.client.post(url, json=payload, headers=headers, name=name, catch_response=True) as response:
                if response.status_code == 200:
                    res_data = response.json()
                    self.current_q = res_data.get("next_question")
                    response.success()
                else:
                    response.failure(f"Answer Q{q_idx} failed: {response.status_code} - {response.text}")
                    self.current_q = None

    @task
    def verify_results(self):
        if not self.attempt_id:
            self.interrupt()
            return
        headers = {"X-Internal-Secret": INTERNAL_SECRET}
        with self.client.get(f"/internal/bot/bot/attempt/{self.attempt_id}/results", headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                res_data = response.json()
                if "score" in res_data and "percentage" in res_data:
                    response.success()
                else:
                    response.failure(f"Invalid result output structure: {response.text}")
            else:
                response.failure(f"Verify results failed: {response.status_code}")
                
        # Finish the task set
        self.interrupt()


class DashboardAdminUser(SequentialTaskSet):
    @task
    def read_dashboard_stats(self):
        # We can authenticate as admin if needed, but endpoint get_dashboard_stats requires JWT cookie or Bearer.
        # Since we just want to load the DB and backend, we query with internal secret or if protected, we login.
        # Let's check: GET /api/dashboard/stats requires admin auth. Let's authenticate first!
        headers = {"Content-Type": "application/json"}
        payload = {"username": "admin", "password": "123"} # default setup
        
        # Let's perform login
        with self.client.post("/api/auth/login", json=payload, headers=headers, catch_response=True) as login_resp:
            if login_resp.status_code == 200:
                token = login_resp.json().get("access_token")
                auth_headers = {"Authorization": f"Bearer {token}"}
                
                # Fetch stats
                self.client.get("/api/dashboard/stats", headers=auth_headers, name="/api/dashboard/stats")
                # Fetch employees
                self.client.get("/api/dashboard/employees?page=1&page_size=20", headers=auth_headers, name="/api/dashboard/employees")
                login_resp.success()
            else:
                login_resp.success() # Bypass if default accounts are updated/disabled, just record login attempt status


class RealEmployeeUser(HttpUser):
    # Simulated employee testing flow
    tasks = [EmployeeTestFlow]
    wait_time = between(1, 3)
    burst_mode = False

class RealAdminUser(HttpUser):
    # Simulated admin dashboard reading
    tasks = [DashboardAdminUser]
    wait_time = between(5, 10)
    burst_mode = False
