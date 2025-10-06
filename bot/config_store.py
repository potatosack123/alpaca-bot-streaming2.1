from __future__ import annotations
from pathlib import Path
import json
import logging
from typing import Dict, Any, Optional, Tuple

try:
    import keyring  # type: ignore
except Exception:
    keyring = None

log = logging.getLogger(__name__)

CONFIG_DIR = Path("config")
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = CONFIG_DIR / "settings.json"
SECRETS_FILE = CONFIG_DIR / "_secrets.json"  # obfuscated fallback (not secure)
SERVICE_NAME = "alpaca_bot"

DEFAULT_SETTINGS = {
    "symbols": "AAPL,MSFT",
    "timeframe": "1m",
    "lunch_skip": True,
    "risk_percent": 1.0,
    "stop_loss_percent": 1.0,
    "take_profit_percent": 2.0,
    "selected_strategy": "BaselineSMA",
    "flatten_on_stop": False,
    "force_mode": "auto",
    "extra_strategy_paths": [],
}

def ensure_runtime_folders() -> None:
    for p in [Path("logs"), Path("backtests"), Path("data")]:
        p.mkdir(parents=True, exist_ok=True)

def load_settings() -> Dict[str, Any]:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            log.exception("Failed reading settings.json: %s", e)
    save_settings(DEFAULT_SETTINGS)
    return DEFAULT_SETTINGS.copy()

def save_settings(settings: Dict[str, Any]) -> None:
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")

def save_credentials(api_key: str, api_secret: str) -> None:
    if keyring:
        keyring.set_password(SERVICE_NAME, "ALPACA_API_KEY", api_key)
        keyring.set_password(SERVICE_NAME, "ALPACA_API_SECRET", api_secret)
        log.info("Saved Alpaca credentials to OS keyring.")
        return
    payload = {"k": _obf(api_key), "s": _obf(api_secret)}
    SECRETS_FILE.write_text(json.dumps(payload), encoding="utf-8")
    log.warning("Keyring unavailable. Saved credentials to %s (obfuscated, NOT secure).", SECRETS_FILE)

def _obf(s: str) -> str:
    return ''.join(chr(ord(c) ^ 0x39) for c in s)

def _deobf(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return ''.join(chr(ord(c) ^ 0x39) for c in s)

def load_credentials() -> Tuple[Optional[str], Optional[str]]:
    if keyring:
        try:
            k = keyring.get_password(SERVICE_NAME, "ALPACA_API_KEY")
            s = keyring.get_password(SERVICE_NAME, "ALPACA_API_SECRET")
            log.info(f"Loaded from keyring - Key starts with: {k[:10] if k else 'None'}")
            return k, s
        except Exception as e:
            log.warning("Keyring error: %s", e)
    if SECRETS_FILE.exists():
        try:
            data = json.loads(SECRETS_FILE.read_text(encoding="utf-8"))
            k = _deobf(data.get("k"))
            s = _deobf(data.get("s"))
            log.info(f"Loaded from secrets file - Key starts with: {k[:10] if k else 'None'}")
            return k, s
        except Exception as e:
            log.exception("Failed reading fallback secrets: %s", e)
    log.warning("No credentials found in keyring or secrets file")
    return None, None

def verify_credentials() -> bool:
    """Check if credentials are saved and valid"""
    k, s = load_credentials()
    if not k or not s:
        log.error("No credentials found")
        return False
    log.info(f"Credentials found - Key starts with: {k[:10]}")
    return True
