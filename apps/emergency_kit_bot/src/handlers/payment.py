from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Order, OrderStatus
from src.utils.states import OrderWizard
from src.utils.text_utils import en_to_fa_digits, format_price
from src.config.config import settings
from src.utils.keyboard_utils import get_main_menu_keyboard

router = Router()

@router.message(OrderWizard.awaiting_payment_receipt, F.photo | F.text)
async def handle_receipt(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    order_id = data.get("order_id")
    order = await session.get(Order, order_id)

    if not order:
        await message.answer("خطایی رخ داد. سفارش یافت نشد.")
        await state.clear()
        return

    if message.photo:
        order.payment_ref = message.photo[-1].file_id
    else:
        order.payment_ref = message.text

    order.status = OrderStatus.PENDING_REVIEW
    await session.commit()

    await message.answer(
        "🙏 رسید شما دریافت شد و پس از تایید مدیریت، سفارش شما وارد مرحله آماده‌سازی می‌شود.\n"
        "سپاس از صبوری شما.",
        reply_markup=get_main_menu_keyboard()
    )

    # Notify Admin
    for admin_id in settings.ADMIN_USER_IDS:
        admin_text = (
            f"🔔 <b>رسید جدید پرداخت!</b>\n\n"
            f"کد سفارش: {en_to_fa_digits(order.order_code)}\n"
            f"مبلغ: {format_price(order.total_price)}\n"
            f"کاربر: {message.from_user.full_name} (@{message.from_user.username})"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ تایید", callback_data=f"adm_approve_{order.id}"),
                InlineKeyboardButton(text="❌ رد", callback_data=f"adm_reject_{order.id}")
            ],
            [InlineKeyboardButton(text="👁 مشاهده جزئیات", callback_data=f"adm_order_{order.id}")]
        ])

        try:
            if message.photo:
                await bot.send_photo(admin_id, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=kb)
            else:
                await bot.send_message(admin_id, text=f"{admin_text}\n\nپیام کاربر: {message.text}", reply_markup=kb)
        except Exception as e:
            print(f"Failed to notify admin {admin_id}: {e}")

    await state.clear()
