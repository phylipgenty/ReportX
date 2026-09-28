"""
Central settings. Everything env-overridable via a .env file (prefix REPORTX_).
See backend/.env.example for the full list.
"""
from pathlib import Path
from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parent.parent      # backend/
PROJECT_DIR = BACKEND_DIR.parent                          # reportx/
FRONTEND_DIR = PROJECT_DIR / "frontend"
SEED_DIR = Path(__file__).resolve().parent / "seed"


class Settings(BaseSettings):
    app_name: str = "ReportX"
    organisation_name: str = "FMDQ Group"
    app_env: str = "dev"

    api_prefix: str = "/api"

    frontend_dir: Path = FRONTEND_DIR
    seed_dir: Path = SEED_DIR
    database_path: Path = BACKEND_DIR / "data" / "reportx.db"
    upload_dir: Path = BACKEND_DIR / "uploads"

    currency: str = "NGN"
    currency_symbol: str = "₦"   # ₦

    # Project ID format (README §4.2 / §53.5): <prefix>-<zero-padded sequence>
    project_id_prefix: str = "PRJ"
    project_id_width: int = 5

    # Completion % strategy: "equal" | "weighted" (README §8 / §53.1 — not final).
    completion_strategy: str = "equal"

    # Load backend/app/seed/demo_projects.json into an empty database on startup.
    seed_demo_projects: bool = False

    # Classification label printed on every report page (as on the April 2025 report).
    report_classification: str = "PUBLIC"

    # Attachments (README §25–§26). Accepted types are unconfirmed (README §53.4).
    upload_extensions: str = ".pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg"
    upload_max_mb: int = 25

    # Sign-in (README §43). ReportX accounts now; an SSO provider can replace
    # services/auth.py's password check later without touching the routers.
    session_hours: int = 12
    session_cookie_name: str = "reportx_session"
    session_cookie_secure: bool = False      # set true when served over HTTPS
    min_password_length: int = 10
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    # First Admin created at startup when the database has no users, so a fresh
    # public deployment never shows the open first-run setup screen. Set both.
    admin_email: str = ""
    admin_password: str = ""
    admin_name: str = "Administrator"

    # Actor recorded in history when the client does not identify the user.
    default_actor: str = "system"

    class Config:
        env_file = ".env"
        env_prefix = "REPORTX_"


settings = Settings()
