import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.user_model import create_user, find_user_by_email


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def main() -> int:
    email = _require_env("ADMIN_EMAIL").lower()
    existing = find_user_by_email(email)
    if existing:
        print("Admin already exists")
        return 0

    payload = {
        "name": _require_env("ADMIN_NAME"),
        "email": email,
        "phone": _require_env("ADMIN_PHONE"),
        "password": _require_env("ADMIN_PASSWORD"),
        "role": "admin",
        "created_at": datetime.utcnow(),
    }

    create_user(payload)
    print("Admin seeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
