"""Authentication helper for test and audit scripts to resolve demo credentials dynamically."""

import os


def get_demo_credentials() -> tuple[str, str]:
    """Return (admin_password, passenger_password) from environment or local .env."""
    admin_pw = os.getenv("SEED_DEMO_ADMIN_PASSWORD")
    user_pw = os.getenv("SEED_DEMO_USER_PASSWORD")
    if not admin_pw or not user_pw:
        env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        clean_v = v.strip().strip('"').strip("'")
                        if k.strip() == "SEED_DEMO_ADMIN_PASSWORD" and not admin_pw:
                            admin_pw = clean_v
                        elif k.strip() == "SEED_DEMO_USER_PASSWORD" and not user_pw:
                            user_pw = clean_v
    return admin_pw or "", user_pw or ""
