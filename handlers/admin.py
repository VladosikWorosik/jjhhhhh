from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from storage import (
    get_all_users, get_withdrawal, delete_withdrawal,
    get_pending_withdrawals, update_user, get_user
)
from keyboards import (
    admin_panel_keyboard, admin_back_keyboard, admin_withdrawal_keyboard
)

router = Router()


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


def admin_only_cb(callback: CallbackQuery) -> bool:
    return is_admin(callback.from_user.id)


class BroadcastState(StatesGroup):
    waiting = State()


# ── /admin ────────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа.")
        return

    all_users   = await get_all_users()
    pending     = await get_pending_withdrawals()
    total_wins  = sum(u.get("wins", 0) for u in all_users.values())
    total_spins = sum(u.get("total_spins", 0) for u in all_users.values())

    text = (
        "🔐 <b>Панель администратора</b>\n\n"
        f"👥 Пользователей: <b>{len(all_users)}</b>\n"
        f"🎲 Всего спинов: <b>{total_spins}</b>\n"
        f"🏆 Всего побед: <b>{total_wins}</b>\n"
        f"💰 Ожидают вывода: <b>{len(pending)}</b>"
    )
    await message.answer(text, reply_markup=admin_panel_keyboard())


# ── Назад в админ-панель ──────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_back")
async def admin_back_cb(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌", show_alert=True)
        return

    all_users   = await get_all_users()
    pending     = await get_pending_withdrawals()
    total_wins  = sum(u.get("wins", 0) for u in all_users.values())
    total_spins = sum(u.get("total_spins", 0) for u in all_users.values())

    text = (
        "🔐 <b>Панель администратора</b>\n\n"
        f"👥 Пользователей: <b>{len(all_users)}</b>\n"
        f"🎲 Всего спинов: <b>{total_spins}</b>\n"
        f"🏆 Всего побед: <b>{total_wins}</b>\n"
        f"💰 Ожидают вывода: <b>{len(pending)}</b>"
    )
    await callback.message.edit_text(text, reply_markup=admin_panel_keyboard())
    await callback.answer()


# ── Заявки на вывод ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_withdrawals")
async def admin_withdrawals(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌", show_alert=True)
        return

    pending = await get_pending_withdrawals()

    if not pending:
        await callback.message.edit_text(
            "💰 <b>Заявки на вывод</b>\n\n✅ Нет ожидающих заявок!",
            reply_markup=admin_back_keyboard()
        )
        await callback.answer()
        return

    lines = [f"💰 <b>Ожидающие заявки ({len(pending)}):</b>\n"]
    for w in pending:
        uname = f"@{w['username']}" if w.get("username") else "—"
        lines.append(
            f"━━━━━━━━━━━━━\n"
            f"📋 <b>#{w['id']}</b>\n"
            f"👤 {w.get('first_name', '?')}  {uname}\n"
            f"🆔 <code>{w['user_id']}</code>\n"
            f"⭐ {w['amount']} Stars\n"
            f"📅 {w['created_at'][:16]}"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=admin_back_keyboard()
    )
    await callback.answer()


# ── Выведено — удалить заявку ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_done_"))
async def admin_done(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌", show_alert=True)
        return

    withdrawal_id = callback.data.removeprefix("adm_done_")
    withdrawal = await get_withdrawal(withdrawal_id)

    if not withdrawal:
        await callback.answer("❌ Заявка не найдена или уже удалена.", show_alert=True)
        await callback.message.delete()
        return

    # Удаляем заявку из JSON
    await delete_withdrawal(withdrawal_id)

    # Уведомляем пользователя
    try:
        await bot.send_message(
            withdrawal["user_id"],
            f"⭐ <b>Ваши Звёзды выведены!</b>\n\n"
            #f"Сумма: <b>{withdrawal['amount']} Telegram Stars</b>\n"
            f"Заявка <b>#{withdrawal_id}</b> выполнена.\n\n"
            f"С уважением Ryze Casino! 🎰"
        )
    except Exception:
        pass

    # Удаляем сообщение с кнопкой у админа
    await callback.message.delete()
    await callback.answer(f"✅ Заявка #{withdrawal_id} удалена!", show_alert=False)


# ── Статистика ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌", show_alert=True)
        return

    all_users   = await get_all_users()
    pending     = await get_pending_withdrawals()
    total_wins  = sum(u.get("wins", 0) for u in all_users.values())
    total_spins = sum(u.get("total_spins", 0) for u in all_users.values())
    total_loss  = sum(u.get("losses", 0) for u in all_users.values())
    win_rate    = (total_wins / total_spins * 100) if total_spins else 0

    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователей: <b>{len(all_users)}</b>\n"
        f"🎲 Спинов: <b>{total_spins}</b>\n"
        f"✅ Побед: <b>{total_wins}</b>\n"
        f"❌ Поражений: <b>{total_loss}</b>\n"
        #f"📈 Винрейт: <b>{win_rate:.1f}%</b>\n\n"
        f"💰 Ожидают вывода: <b>{len(pending)}</b>"
    )
    await callback.message.edit_text(text, reply_markup=admin_back_keyboard())
    await callback.answer()


# ── Игроки ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌", show_alert=True)
        return

    all_users = await get_all_users()
    sorted_u  = sorted(all_users.values(), key=lambda u: u.get("wins", 0), reverse=True)

    lines = [f"👥 <b>Игроки ({len(sorted_u)}):</b>\n"]
    for i, u in enumerate(sorted_u[:20], 1):
        uname   = f"@{u['username']}" if u.get("username") else u.get("first_name", "?")
        ban_ico = "🚫" if u.get("is_banned") else ""
        lines.append(
            f"{i}. {ban_ico}{uname} | "
            f"✅{u.get('wins',0)} ❌{u.get('losses',0)} "
            f"🎲{u.get('total_spins',0)}"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=admin_back_keyboard()
    )
    await callback.answer()


# ── Рассылка ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌", show_alert=True)
        return

    await state.set_state(BroadcastState.waiting)
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\n"
        "Отправьте сообщение — я разошлю его всем пользователям.\n"
        "Для отмены — /cancel"
    )
    await callback.answer()


@router.message(BroadcastState.waiting)
async def do_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Рассылка отменена.")
        return

    all_users = await get_all_users()
    ok = fail = 0

    status = await message.answer(f"📤 Рассылаю для {len(all_users)} пользователей…")

    for uid_str, u in all_users.items():
        if u.get("is_banned"):
            continue
        try:
            await bot.copy_message(
                chat_id=int(uid_str),
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            ok += 1
        except Exception:
            fail += 1

    await state.clear()
    await bot.edit_message_text(
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"✅ Доставлено: {ok}\n"
        f"❌ Ошибки: {fail}",
        chat_id=message.chat.id,
        message_id=status.message_id
    )


# ── Бан / Разбан ──────────────────────────────────────────────────────────────

@router.message(Command("ban"))
async def cmd_ban(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /ban <user_id>")
        return
    try:
        tid = int(args[1])
        await update_user(tid, is_banned=True)
        await message.answer(f"🚫 Пользователь {tid} заблокирован.")
        try:
            await bot.send_message(tid, "🚫 Вы заблокированы в боте.")
        except Exception:
            pass
    except (ValueError, TypeError):
        await message.answer("❌ Некорректный ID.")


@router.message(Command("unban"))
async def cmd_unban(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /unban <user_id>")
        return
    try:
        tid = int(args[1])
        await update_user(tid, is_banned=False)
        await message.answer(f"✅ Пользователь {tid} разблокирован.")
        try:
            await bot.send_message(tid, "✅ Вы разблокированы в боте.")
        except Exception:
            pass
    except (ValueError, TypeError):
        await message.answer("❌ Некорректный ID.")