from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models import Order, OrderStatus, Product, User
from src.config.config import settings
from src.utils.text_utils import en_to_fa_digits, format_price, get_status_label

router = Router()

class AdminState(StatesGroup):
    changing_price = State()
    changing_stock = State()

def is_admin(user_id: int):
    return user_id in settings.ADMIN_USER_IDS

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 مشاهده سفارش‌ها", callback_data="adm_list_orders")],
        [InlineKeyboardButton(text="💰 مدیریت قیمت و موجودی", callback_data="adm_manage_products")],
        [InlineKeyboardButton(text="📢 ارسال پیام همگانی", callback_data="adm_broadcast")]
    ])

    await message.answer("🛠 <b>پنل مدیریت</b>\nخوش آمدید. یکی از گزینه‌ها را انتخاب کنید:", reply_markup=kb)

@router.callback_query(F.data == "adm_list_orders")
async def list_orders(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id): return

    result = await session.execute(
        select(Order).order_by(Order.created_at.desc()).limit(10)
    )
    orders = result.scalars().all()

    if not orders:
        await callback.answer("سفارشی یافت نشد.")
        return

    text = "📋 <b>۱۰ سفارش اخیر:</b>\n\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for o in orders:
        text += f"🔹 {en_to_fa_digits(o.order_code)} - {get_status_label(o.status.value)}\n"
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"سفارش {en_to_fa_digits(o.order_code)}", callback_data=f"adm_order_{o.id}")])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("adm_order_"))
async def view_order(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id): return

    order_id = int(callback.data.split("_")[2])
    order = await session.get(Order, order_id)

    if not order:
        await callback.answer("سفارش یافت نشد.")
        return

    product = await session.get(Product, order.product_id)
    user = await session.get(User, order.user_id)

    text = (
        f"📑 <b>جزئیات سفارش {en_to_fa_digits(order.order_code)}</b>\n\n"
        f"👤 مشتری: {user.full_name} (آیدی: {en_to_fa_digits(user.telegram_user_id)})\n"
        f"📦 محصول: {product.title_fa}\n"
        f"🔢 تعداد: {en_to_fa_digits(order.quantity)}\n"
        f"💰 مبلغ کل: {format_price(order.total_price)}\n"
        f"📍 آدرس: {order.address_json['province']}، {order.address_json['city']}، {order.address_json['full_address']}\n"
        f"📊 وضعیت: {get_status_label(order.status.value)}\n"
        f"💳 رفرنس پرداخت: <code>{en_to_fa_digits(order.payment_ref) or 'ندارد'}</code>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تایید پرداخت", callback_data=f"adm_approve_{order.id}"),
            InlineKeyboardButton(text="❌ رد پرداخت", callback_data=f"adm_reject_{order.id}")
        ],
        [InlineKeyboardButton(text="🚚 ارسال شد", callback_data=f"adm_status_{order.id}_SHIPPED")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="adm_list_orders")]
    ])

    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("adm_approve_"))
async def approve_order(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    if not is_admin(callback.from_user.id): return

    order_id = int(callback.data.split("_")[2])
    order = await session.get(Order, order_id)
    user = await session.get(User, order.user_id)

    order.status = OrderStatus.PAID
    await session.commit()

    await callback.answer("✅ سفارش تایید شد.")

    confirm_text = "\n\n✅ <b>تایید شد</b>"
    if callback.message.photo:
        await callback.message.edit_caption(caption=(callback.message.caption or "") + confirm_text)
    else:
        await callback.message.edit_text(text=(callback.message.text or "") + confirm_text)

    await bot.send_message(
        user.telegram_user_id,
        f"✅ پرداخت سفارش <code>{en_to_fa_digits(order.order_code)}</code> تایید شد!\n"
        "سفارش شما در حال آماده‌سازی است."
    )

@router.callback_query(F.data == "adm_manage_products")
async def manage_products(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id): return

    result = await session.execute(select(Product))
    products = result.scalars().all()

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for p in products:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"💰 قیمت {p.sku}", callback_data=f"adm_price_{p.id}"),
            InlineKeyboardButton(text=f"📦 موجودی {p.sku}", callback_data=f"adm_stock_{p.id}")
        ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="adm_back")])

    await callback.message.edit_text("🔧 مدیریت محصولات:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "adm_back")
async def admin_back(callback: CallbackQuery):
    await admin_panel(callback.message)
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data.startswith("adm_price_"))
async def start_change_price(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[2])
    await state.update_data(product_id=product_id)
    await state.set_state(AdminState.changing_price)
    await callback.message.answer("💸 قیمت جدید را به تومان وارد کنید (مثلاً ۲۰۰۰۰۰۰):")
    await callback.answer()

@router.message(AdminState.changing_price)
async def change_price(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message.from_user.id): return

    try:
        new_price = int(message.text)
        data = await state.get_data()
        product = await session.get(Product, data['product_id'])
        product.price_toman = new_price
        await session.commit()
        await message.answer(f"✅ قیمت محصول {product.sku} به {format_price(new_price)} تغییر یافت.")
    except ValueError:
        await message.answer("❌ عدد نامعتبر است.")

    await state.clear()

@router.callback_query(F.data.startswith("adm_reject_"))
async def reject_order(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    if not is_admin(callback.from_user.id): return

    order_id = int(callback.data.split("_")[2])
    order = await session.get(Order, order_id)
    user = await session.get(User, order.user_id)

    order.status = OrderStatus.WAITING_PAYMENT
    await session.commit()

    await callback.answer("❌ سفارش رد شد.")

    reject_text = "\n\n❌ <b>رد شد</b>"
    if callback.message.photo:
        await callback.message.edit_caption(caption=(callback.message.caption or "") + reject_text)
    else:
        await callback.message.edit_text(text=(callback.message.text or "") + reject_text)

    await bot.send_message(
        user.telegram_user_id,
        f"❌ رسید پرداخت سفارش <code>{en_to_fa_digits(order.order_code)}</code> مورد تایید قرار نگرفت.\n"
        "لطفاً دوباره بررسی کرده و رسید صحیح را ارسال کنید یا با پشتیبانی تماس بگیرید."
    )

@router.callback_query(F.data.startswith("adm_status_"))
async def change_order_status(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    if not is_admin(callback.from_user.id): return

    parts = callback.data.split("_")
    order_id = int(parts[2])
    new_status_str = parts[3]

    order = await session.get(Order, order_id)
    user = await session.get(User, order.user_id)

    order.status = OrderStatus[new_status_str]
    await session.commit()

    status_label = get_status_label(new_status_str)
    await callback.answer(f"✅ وضعیت به {status_label} تغییر یافت.")

    await bot.send_message(
        user.telegram_user_id,
        f"📦 وضعیت سفارش <code>{en_to_fa_digits(order.order_code)}</code> به <b>{status_label}</b> تغییر یافت."
    )
