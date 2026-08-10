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
