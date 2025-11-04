import os
import time
from typing import Optional, Dict


class FlaggedQuestionTracker:
    def __init__(self, ttl_minutes: int = None):
        self.ttl_minutes = ttl_minutes or int(os.getenv("FLAGGED_TRACKING_TTL_MINUTES", "5"))
        self.ttl_seconds = self.ttl_minutes * 60
        self._flagged_attempts: Dict[str, float] = {}

    def record_flagged(self, user_id: str) -> None:
        self._flagged_attempts[user_id] = time.time()
        self._cleanup_expired()

    def check_recovery(self, user_id: str) -> bool:
        self._cleanup_expired()
        if user_id not in self._flagged_attempts:
            return False

        flagged_time = self._flagged_attempts[user_id]
        time_since_flagged = time.time() - flagged_time
        return time_since_flagged <= self.ttl_seconds

    def record_success(self, user_id: str) -> bool:
        was_recovery = self.check_recovery(user_id)
        if was_recovery and user_id in self._flagged_attempts:
            del self._flagged_attempts[user_id]
        return was_recovery

    def _cleanup_expired(self) -> None:
        current_time = time.time()
        expired_users = [
            user_id
            for user_id, flagged_time in self._flagged_attempts.items()
            if current_time - flagged_time > self.ttl_seconds
        ]
        for user_id in expired_users:
            del self._flagged_attempts[user_id]


_tracker_instance: Optional[FlaggedQuestionTracker] = None


def get_tracker() -> FlaggedQuestionTracker:
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = FlaggedQuestionTracker()
    return _tracker_instance
