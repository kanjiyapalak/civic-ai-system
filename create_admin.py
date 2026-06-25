import argparse
import sys
from datetime import datetime
from getpass import getpass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.user_model import create_user, find_user_by_email


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--phone", required=True)
    parser.add_argument("--password")
    args = parser.parse_args()

    email = args.email.strip().lower()
    if find_user_by_email(email):
        print("Email already registered")
        return 1

    password = args.password or getpass("Admin password: ")
    if not password:
        print("Password is required")
        return 1

    create_user(
        {
            "name": args.name,
            "email": email,
            "phone": args.phone,
            "password": password,
            "role": "admin",
            "created_at": datetime.utcnow(),
        }
    )
    print("Admin user created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
