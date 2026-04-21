"""
Edge node configuration.

Settings are read from `/etc/yuz-tanima/edge.env` on the Pi (populated during
provisioning) or from `./.env` during local development.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent

# Prefer /etc path in production; fall back to repo-local .env for dev
_PROD_ENV = Path("/etc/yuz-tanima/edge.env")
_DEV_ENV = BASE_DIR / ".env"
_ENV_FILE = _PROD_ENV if _PROD_ENV.exists() else _DEV_ENV


class EdgeSettings(BaseSettings):
    """Runtime settings for the edge node."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Identity ---
    device_id: str = Field(..., description="UUID assigned during provisioning")
    school_id: int = Field(..., description="Associated school tenant ID")
    api_key: str = Field(..., description="Secret shared with VPS, used for HMAC signing")

    # --- Server endpoint ---
    server_url: str = Field(
        default="https://api.yuztanima.com",
        description="Base URL of the central VPS",
    )
    api_timeout: int = 10  # seconds

    # --- Camera ---
    camera_index: int = 0
    camera_width: int = 640
    camera_height: int = 480
    camera_fps: int = 15

    # --- Recognition ---
    recognition_tolerance: float = 0.55  # lower = stricter
    recognition_min_interval_ms: int = 2500  # debounce same-person detection
    recognizer_backend: str = "dlib"  # "dlib" or "insightface"

    # --- Turnstile / GPIO ---
    gpio_relay_pin: int = 17
    relay_pulse_ms: int = 500
    gpio_led_ok_pin: int = 22
    gpio_led_fail_pin: int = 27
    gpio_buzzer_pin: int = 23
    fail_safe_on_error: bool = True  # turnstile stays locked on error

    # --- LCD (I2C) ---
    lcd_enabled: bool = True
    lcd_i2c_address: int = 0x27
    lcd_cols: int = 16
    lcd_rows: int = 2

    # --- Local storage ---
    local_db_path: Path = Field(default=BASE_DIR / "data" / "edge.db")
    snapshot_dir: Path = Field(default=BASE_DIR / "data" / "snapshots")

    # --- Sync ---
    heartbeat_interval: int = 30        # seconds
    encoding_sync_interval: int = 300   # 5 min
    log_sync_interval: int = 60
    log_batch_size: int = 50
    max_pending_logs: int = 10_000

    # --- Logging ---
    log_level: str = "INFO"
    log_dir: Path = Field(default=BASE_DIR / "logs")

    # --- OTA updates ---
    update_check_interval: int = 3600   # 1h
    update_public_key_path: Path = Field(
        default=Path("/etc/yuz-tanima/update_pubkey.pem")
    )


# Singleton instance — imported from everywhere
settings = EdgeSettings()  # type: ignore[call-arg]

# Ensure required directories exist
for _d in (settings.local_db_path.parent, settings.snapshot_dir, settings.log_dir):
    _d.mkdir(parents=True, exist_ok=True)