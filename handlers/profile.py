import time
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from config import SPIN_COOLDOWN
from storage import get_user, get_all_users
from keyboards import profile_keyboard, back_to_menu_keyboard
from handlers.start import check_subscription

router = Router()


def rank(wins: int) -> str:
    if wins >= 50: return "👑 Легенда"
    if wins >= 20: return "💎 Эксперт"
    if wins >= 10: return "🥇 Мастер"
    if wins >= 5:  return "🥈 Игрок"
    if wins >= 1:  return "🥉 Новичок"
    return "🎮 Начинающий"


def fmt_cooldown(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


def build_profile(user: dict) -> str:
    wins   = user.get("wins", 0)
    losses = user.get("losses", 0)
    spins  = user.get("total_spins", 0)
    rate   = (wins / spins * 100) if spins else 0

    uname  = f"@{user['username']}" if user.get("username") else "—"

    now     = time.time()
    elapsed = now - user.get("last_spin", 0)
    if elapsed >= SPIN_COOLDOWN:
        spin_status = "✅ Можно крутить!"
    else:
        left = int(SPIN_COOLDOWN - elapsed)
        spin_status = f"⏰ Следующий спин через {fmt_cooldown(left)}"

    return (
        "👤 <b>Профиль</b>\n\n"
        f"🆔 <b>ID:</b> <code>{user['user_id']}</code>\n"
        f"📱 <b>Username:</b> {uname}\n"
        f"👋 <b>Имя:</b> {user.get('first_name', '?')}\n"
        #f"🏅 <b>Ранг:</b> {rank(wins)}\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📊 <b>Статистика:</b>\n"
        f"🎲 Спинов: <b>{spins}</b>\n"
        f"✅ Побед: <b>{wins}</b>\n"
        f"❌ Поражений: <b>{losses}</b>\n"
        #f"📈 Винрейт: <b>{rate:.1f}%</b>\n\n"
        "━━━━━━━━━━━━━━━\n"
        f"🎰 {spin_status}\n\n"
        f"📅 Регистрация: {user.get('registered_at', '?')[:10]}"
    )


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, callback.from_user.id):
        await callback.answer("❌ Подпишись на канал!", show_alert=True)
        return

    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Напиши /start", show_alert=True)
        return

    await callback.message.edit_text(build_profile(user), reply_markup=profile_keyboard())
    await callback.answer()


@router.callback_query(F.data == "top")
async def show_top(callback: CallbackQuery):
    all_users = await get_all_users()
    if not all_users:
        await callback.answer("Нет данных!", show_alert=True)
        return

    sorted_users = sorted(all_users.values(), key=lambda u: u.get("wins", 0), reverse=True)

    medals = ["🥇", "🥈", "🥉"] + ["🎖️"] * 17
    lines = ["🏆 <b>Топ-10 игроков</b>\n"]

    for i, u in enumerate(sorted_users[:10]):
        name = f"@{u['username']}" if u.get("username") else u.get("first_name", "Аноним")
        lines.append(f"{medals[i]} {i+1}. {name} — <b>{u.get('wins', 0)} побед</b>")

    lines.append("\n🎰 <i>Крути и попадай в топ!</i>")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_menu_keyboard()
    )
    await callback.answer()