from contextvars import ContextVar
from typing import Optional

# Context var holding current request's authenticated user id (string UUID)
_current_user_id: ContextVar[Optional[str]] = ContextVar("_current_user_id", default=None)

def set_current_user_id(user_id: Optional[str]) -> None:
    _current_user_id.set(user_id)

def get_current_user_id() -> Optional[str]:
    return _current_user_id.get()


