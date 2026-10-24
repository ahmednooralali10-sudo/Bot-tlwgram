# ملف: info.py
import os
import re
import json
import requests

# ==========================================
# CONFIGURATION
# ==========================================
# ⚠️ تم وضع رابط API عام لجلب الاسم واللفل
INFO_API_URL = "https://freefireinfo-zy9l.onrender.com/api/v1/player-profile" 
BAN_API_URL  = "https://ff.garena.com/api/antihack/check_banned"

BAN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "referer": "https://ff.garena.com/en/support/",
    "x-requested-with": "B6FksShzIgjfrYImLpTsadjS86sddhFH",
}

def check_account_status(uid):
    """Returns (status, name, level) where status ∈ {'banned','clean','failed'}."""
    session = requests.Session()
    ban_result = None
    name = "غير معروف"
    level = "غير معروف"

    # --- Ban check ---
    try:
        ban_res = session.get(f"{BAN_API_URL}?lang=en&uid={uid}", headers=BAN_HEADERS, timeout=8)
        if ban_res.status_code == 200:
            try:
                ban_data = ban_res.json().get("data", {})
                ban_result = bool(ban_data.get("is_banned", 0))
            except Exception:
                ban_result = None
    except Exception:
        ban_result = None

    # --- Info check ---
    if "USE YOUR" not in INFO_API_URL and "http" in INFO_API_URL:
        try:
            info_res = session.get(f"{INFO_API_URL}?uid={uid}", timeout=8)
            if info_res.status_code == 200:
                raw = info_res.json()
                # جلب الاسم واللفل من الـ API (حسب هيكل البيانات الذي يرجع)
                data = raw.get("data", raw) 
                name = data.get("nickname") or data.get("name") or data.get("accountname") or "غير معروف"
                level = data.get("level") or data.get("account_level") or "غير معروف"
        except Exception:
            pass

    if ban_result is None:
        return "failed", name, level
    return ("banned" if ban_result else "clean"), name, level
