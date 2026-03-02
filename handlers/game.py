import asyncio
import time
import random

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from config import ADMIN_IDS, SPIN_COOLDOWN, WIN_AMOUNT
from storage import get_user, update_user, add_withdrawal, set_withdrawal_message_id
from keyboards import main_menu_keyboard, admin_withdrawal_keyboard
from handlers.start import check_subscription

router = Router()

# Выигрышные значения кубика 🎰 (Telegram dice)
# Слот возвращает 1–64; 64 = 777 (джекпот)
WIN_VALUES = {64, 1, 22, 43}


def fmt_cooldown(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m} мин. {s} сек." if m else f"{s} сек."


async def notify_admins(bot: Bot, withdrawal: dict):
    """Отправить уведомление всем админам."""
    username_str = f"@{withdrawal['username']}" if withdrawal.get("username") else "—"
    text = (
        f"⭐ <b>Новый вывод #{withdrawal['id']}</b>\n\n"
        f"👤 <b>Имя:</b> {withdrawal.get('first_name', '?')}\n"
        f"📱 <b>Username:</b> {username_str}\n"
        f"🆔 <b>ID:</b> <code>{withdrawal['user_id']}</code>\n"
        f"💫 <b>Сумма:</b> {withdrawal['amount']} Stars\n"
        f"📅 <b>Время:</b> {withdrawal['created_at']}\n\n"
        #f"Выведите звёзды и нажмите кнопку ниже."
    )

    for admin_id in ADMIN_IDS:
        try:
            msg = await bot.send_message(
                admin_id,
                text,
                reply_markup=admin_withdrawal_keyboard(withdrawal["id"])
            )
            await set_withdrawal_message_id(withdrawal["id"], msg.message_id)
        except Exception as e:
            print(f"[ADMIN NOTIFY] Ошибка для {admin_id}: {e}")


@router.callback_query(F.data == "spin")
async def handle_spin(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id

    # Проверяем подписку
    if not await check_subscription(bot, user_id):
        await callback.answer("❌ Сначала подпишись на канал!", show_alert=True)
        return

    user = await get_user(user_id)
    if not user:
        await callback.answer("Напиши /start", show_alert=True)
        return

    # Проверяем кулдаун
    now = time.time()
    elapsed = now - user.get("last_spin", 0)
    if elapsed < SPIN_COOLDOWN:
        left = int(SPIN_COOLDOWN - elapsed)
        await callback.answer(
            f"⏳ Подождите ещё {fmt_cooldown(left)}!",
            show_alert=True
        )
        return

    await callback.answer("🎰 Запускаем барабаны...")

    # Обновляем время спина
    await update_user(user_id, last_spin=now)

    # Сообщение-заглушка пока крутится
    info_msg = await callback.message.answer(
        "🎰 <b>Барабаны крутятся…</b>"
    )

    # Отправляем кубик-слот
    dice_msg = await bot.send_dice(callback.message.chat.id, emoji="🎰")
    value = dice_msg.dice.value

    # Ждём анимацию
    await asyncio.sleep(5)

    is_win = value in WIN_VALUES

    # Обновляем статистику
    spins = user.get("total_spins", 0) + 1
    if is_win:
        wins = user.get("wins", 0) + 1
        await update_user(user_id, total_spins=spins, wins=wins)
    else:
        losses = user.get("losses", 0) + 1
        await update_user(user_id, total_spins=spins, losses=losses)

    # ── ПОБЕДА ──────────────────────────────────────────
    if is_win:
        # Создаём заявку
        fresh_user = await get_user(user_id)
        withdrawal = await add_withdrawal(user_id, fresh_user, WIN_AMOUNT)

        result_text = (
            "🎉 <b>Поздравляем! Вы выиграли!</b>\n\n"
            "⭐ Звёзды будут начислены в течении ~24 часов\n\n"
            "🔄 Следующий спин — через <b>25 минут</b>"
        )

        # Уведомляем админов
        await notify_admins(bot, withdrawal)

    # ── ПРОИГРЫШ ────────────────────────────────────────
    else:
        lose_phrases = [
            "Не повезло, но удача рядом! 🍀",
            "В следующий раз точно! 💪",
            "Барабаны ещё покажут тебе победу! 🎲",
            "Не сдавайся, ты почти у цели! 🏆",
            "Один шаг до победы! ⚡",
        ]
        result_text = (
            "😔 <b>Вы проиграли…</b>\n\n"
            #f"💬 {random.choice(lose_phrases)}\n\n"
            "⏰ Попробуйте снова через <b>25 минут</b>!"
        )

    # Редактируем информационное сообщение
    try:
        await bot.edit_message_text(
            result_text,
            chat_id=callback.message.chat.id,
            message_id=info_msg.message_id,
            reply_markup=main_menu_keyboard()
        )
    except Exception:
        await bot.send_message(
            callback.message.chat.id,
            result_text,
            reply_markup=main_menu_keyboard()
        )