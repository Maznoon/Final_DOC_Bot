from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.config.config import settings

router = Router()

class SupportState(StatesGroup):
    waiting_for_message = State()
    admin_replying = State()

@router.message(F.text == "ارتباط با پشتیبانی")
async def support_start(message: Message, state: FSMContext):
    await state.set_state(SupportState.waiting_for_message)
    await message.answer(
        f"📩 لطفاً پیام خود را بنویسید تا برای تیم پشتیبانی ارسال شود.\n"
        f"آیدی پشتیبانی مستقیم: {settings.SUPPORT_CONTACT}"
    )

@router.message(SupportState.waiting_for_message)
async def forward_to_admin(message: Message, state: FSMContext, bot: Bot):
    await state.clear()

    for admin_id in settings.ADMIN_USER_IDS:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 پاسخ", callback_data=f"support_reply_{message.from_user.id}")]
        ])

        await bot.send_message(
            admin_id,
            f"📨 <b>پیام جدید از کاربر</b>\n"
            f"نام: {message.from_user.full_name}\n"
            f"آیدی: <code>{message.from_user.id}</code>\n\n"
            f"متن پیام:\n{message.text}",
            reply_markup=kb
        )

    await message.answer("✅ پیام شما برای پشتیبانی ارسال شد. به زودی پاسخ خود را دریافت خواهید کرد.")

@router.callback_query(F.data.startswith("support_reply_"))
async def admin_reply_start(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[2])
    await state.update_data(reply_to_user_id=user_id)
    await state.set_state(SupportState.admin_replying)
    await callback.message.answer(f"✍️ در حال پاسخ به کاربر <code>{user_id}</code>. پیام خود را بفرستید:")
    await callback.answer()

@router.message(SupportState.admin_replying)
async def admin_send_reply(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_id = data.get("reply_to_user_id")

    try:
        await bot.send_message(
            user_id,
            f"👨‍💻 <b>پاسخ پشتیبانی:</b>\n\n{message.text}"
        )
        await message.answer("✅ پاسخ برای کاربر ارسال شد.")
    except Exception as e:
        await message.answer(f"❌ خطا در ارسال پاسخ: {e}")

    await state.clear()
