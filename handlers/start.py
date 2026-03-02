from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from config import CHANNEL_ID
from keyboards import main_menu_keyboard, subscribe_keyboard, back_to_menu_keyboard

router = Router()


async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status not in ["left", "kicked", "banned"]
    except Exception:
        return False


async def get_channel_link(bot: Bot) -> str:
    try:
        chat = await bot.get_chat(CHANNEL_ID)
        if chat.invite_link:
            return chat.invite_link
        if chat.username:
            return f"https://t.me/{chat.username}"
    except Exception:
        pass
    return f"https://t.me/{CHANNEL_ID.lstrip('@')}"


WELCOME_TEXT = (
    "🎰 <b>Добро пожаловать в Ryze Casino!</b>\n\n"
    "🎲 Испытай свою удачу!\n"
    "⭐ Выигрывай <b>Звёзды</b>\n"
    #"🏆 Соревнуйся с другими игроками\n\n"
    "<b>Правила:</b>\n"
    "• Нажми <b>🎰 Крутить</b>\n"
    "• 3 одинаковых - выигрыш!\n"
    #"• Звёзды придут в течение <b>~24 часов</b>\n"
    "• Крутить можно раз в <b>25 минут</b>"
)


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    is_sub = await check_subscription(bot, message.from_user.id)

    if not is_sub:
        link = await get_channel_link(bot)
        await message.answer(
            "🔒 <b>Доступ закрыт!</b>\n\n"
            "Подпишись на канал и нажми <b>✅ Проверить подписку</b>",
            reply_markup=subscribe_keyboard(link)
        )
        return

    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n{WELCOME_TEXT}",
        reply_markup=main_menu_keyboard()
    )


@router.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, bot: Bot):
    is_sub = await check_subscription(bot, callback.from_user.id)

    if is_sub:
        await callback.message.edit_text(
            f"✅ <b>Подписка подтверждена!</b>\n\n{WELCOME_TEXT}",
            reply_markup=main_menu_keyboard()
        )
        await callback.answer("✅ Добро пожаловать!")
    else:
        await callback.answer("❌ Вы ещё не подписались!", show_alert=True)


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, bot: Bot):
    is_sub = await check_subscription(bot, callback.from_user.id)
    if not is_sub:
        link = await get_channel_link(bot)
        await callback.message.edit_text(
            "🔒 <b>Доступ закрыт!</b>\n\nПодпишись на канал.",
            reply_markup=subscribe_keyboard(link)
        )
        return

    await callback.message.edit_text(
        f"🏠 <b>Главное меню</b>\n\n{WELCOME_TEXT}",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "rules")
async def show_rules(callback: CallbackQuery):
    text = (
        "📋 <b>Правила игры</b>\n\n"
        "🎰 <b>Как играть:</b>\n"
        "Нажми кнопку «Крутить».\n"
        "Выпадет 3 одинаковых символа - выигрыш!\n\n"
        "⭐ <b>Выигрыш:</b>\n"
        "15 Звёзд зачисляются в течение ~24 часов.\n\n"
        "⏰ <b>Кулдаун:</b>\n"
        "Между крутками - 25 минут.\n\n"
        "🏆 <b>Рейтинг:</b>\n"
        "Соревнуйся с другими — попади в топ!"
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_keyboard())
    await callback.answer()