# ملف: checker.py
import info

def get_player_info(uid):
    """دالة تستدعي ملف info.py لجلب البيانات"""
    status, name, level = info.check_account_status(uid)
    
    return {
        "name": name, 
        "level": level,
        "status": status
    }
