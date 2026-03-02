import json
import os
import asyncio
from datetime import datetime
from config import DATA_DIR, USERS_FILE, WITHDRAWALS_FILE

# Лок для безопасной записи
_lock = asyncio.Lock()


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _read_json(path: str) -> dict | list:
    _ensure_dir()
    if not os.path.exists(path):
        # users — словарь, withdrawals — список
        default = {} if "users" in path else []
        _write_json_sync(path, default)
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            default = {} if "users" in path else []
            return default


def _write_json_sync(path: str, data):
    _ensure_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────
#  USERS
# ──────────────────────────────────────────────

async def get_user(user_id: int) -> dict | None:
    users = _read_json(USERS_FILE)
    return users.get(str(user_id))


async def save_user(user_id: int, data: dict):
    async with _lock:
        users = _read_json(USERS_FILE)
        users[str(user_id)] = data
        _write_json_sync(USERS_FILE, users)


async def get_all_users() -> dict:
    return _read_json(USERS_FILE)


async def create_user(user_id: int, username: str,
                      first_name: str, last_name: str) -> dict:
    existing = await get_user(user_id)
    if existing:
        return existing

    user = {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "wins": 0,
        "losses": 0,
        "total_spins": 0,
        "last_spin": 0,
        "is_banned": False,
        "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    await save_user(user_id, user)
    return user


async def update_user(user_id: int, **kwargs) -> dict | None:
    user = await get_user(user_id)
    if not user:
        return None
    user.update(kwargs)
    await save_user(user_id, user)
    return user


# ──────────────────────────────────────────────
#  WITHDRAWALS
# ──────────────────────────────────────────────

async def get_all_withdrawals() -> list:
    return _read_json(WITHDRAWALS_FILE)


async def get_withdrawal(withdrawal_id: str) -> dict | None:
    withdrawals = await get_all_withdrawals()
    for w in withdrawals:
        if w["id"] == withdrawal_id:
            return w
    return None


async def add_withdrawal(user_id: int, user: dict, amount: int) -> dict:
    async with _lock:
        withdrawals = _read_json(WITHDRAWALS_FILE)

        # Генерируем ID
        new_id = f"W{len(withdrawals) + 1:04d}"

        withdrawal = {
            "id": new_id,
            "user_id": user_id,
            "username": user.get("username", ""),
            "first_name": user.get("first_name", ""),
            "amount": amount,
            "status": "pending",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin_message_id": None
        }

        withdrawals.append(withdrawal)
        _write_json_sync(WITHDRAWALS_FILE, withdrawals)
        return withdrawal


async def set_withdrawal_message_id(withdrawal_id: str, message_id: int):
    async with _lock:
        withdrawals = _read_json(WITHDRAWALS_FILE)
        for w in withdrawals:
            if w["id"] == withdrawal_id:
                w["admin_message_id"] = message_id
                break
        _write_json_sync(WITHDRAWALS_FILE, withdrawals)


async def delete_withdrawal(withdrawal_id: str):
    async with _lock:
        withdrawals = _read_json(WITHDRAWALS_FILE)
        withdrawals = [w for w in withdrawals if w["id"] != withdrawal_id]
        _write_json_sync(WITHDRAWALS_FILE, withdrawals)


async def get_pending_withdrawals() -> list:
    withdrawals = await get_all_withdrawals()
    return [w for w in withdrawals if w["status"] == "pending"]