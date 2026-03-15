import json
import os

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".pyreaderpdf_config.json")

DEFAULTS = {
    "view_mode":    "continuous",   # "continuous" | "single"
    "default_zoom": 1.5,
    "theme":        "dark",
}


def load() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return dict(DEFAULTS)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**DEFAULTS, **data}
    except Exception:
        return dict(DEFAULTS)


def save(config: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def get(key: str):
    return load().get(key, DEFAULTS.get(key))


def set(key: str, value):
    cfg = load()
    cfg[key] = value
    save(cfg)