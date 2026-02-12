import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.models import Product, Order, OrderStatus, PaymentMethod, User
from src.utils.states import OrderWizard
from src.utils.provinces import PROVINCES
from src.utils.text_utils import en_to_fa_digits, format_price
from src.utils.keyboard_utils import get_main_menu_keyboard
from src.config.config import settings
from src.handlers.products import list_products
from src.services.payment_service import MockGatewayProvider

router = Router()

@router.message(F.text == "ثبت سفارش")
async def start_order_from_menu(message: Message, session: AsyncSession):
    await list_products(message, session)

def get_provinces_keyboard(page: int = 0):
    page_size = 10
    start = page * page_size
    end = start + page_size
    current_provinces = PROVINCES[start:end]

    builder = InlineKeyboardMarkup(inline_keyboard=[])
    # 2 columns
    for i in range(0, len(current_provinces), 2):
        row = [InlineKeyboardButton(text=current_provinces[i], callback_data=f"prov_{current_provinces[i]}")]
        if i + 1 < len(current_provinces):
            row.append(InlineKeyboardButton(text=current_provinces[i+1], callback_data=f"prov_{current_provinces[i+1]}"))
        builder.inline_keyboard.append(row)

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ قبلی", callback_data=f"prov_page_{page-1}"))
    if end < len(PROVINCES):
        nav_row.append(InlineKeyboardButton(text="بعدی ➡️", callback_data=f"prov_page_{page+1}"))

    if nav_row:
        builder.inline_keyboard.append(nav_row)

    return builder

@router.callback_query(F.data.startswith("buy_"))
async def start_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    product_id = int(callback.data.split("_")[1])
    product = await session.get(Product, product_id)

    if not product or product.stock <= 0:
        await callback.answer("متأسفانه این محصول در حال حاضر موجود نیست.")
        return

    await state.update_data(product_id=product_id, product_title=product.title_fa, price=product.price_toman)
    await state.set_state(OrderWizard.selecting_quantity)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=en_to_fa_digits(str(i)), callback_data=f"qty_{i}") for i in range(1, 6)],
        [InlineKeyboardButton(text=en_to_fa_digits(str(i)), callback_data=f"qty_{i}") for i in range(6, 11)],
        [InlineKeyboardButton(text="❌ انصراف", callback_data="cancel_order")]
    ])

    await callback.message.answer(f"📦 محصول انتخاب شده: <b>{product.title_fa}</b>\n\nلطفاً تعداد مورد نظر خود را انتخاب کنید (۱ تا ۱۰):", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("qty_"), OrderWizard.selecting_quantity)
async def select_quantity(callback: CallbackQuery, state: FSMContext):
    qty = int(callback.data.split("_")[1])
    await state.update_data(quantity=qty)
    await state.set_state(OrderWizard.entering_name)
    await callback.message.answer("👤 نام و نام خانوادگی خود را وارد کنید:")
    await callback.answer()

@router.message(OrderWizard.entering_name)
async def enter_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(OrderWizard.entering_phone)
    await message.answer("📞 شماره موبایل خود را وارد کنید (مثال: ۰۹۱۲۳۴۵۶۷۸۹):")

@router.message(OrderWizard.entering_phone)
async def enter_phone(message: Message, state: FSMContext):
    phone = message.text
    # Basic Iranian phone validation
    if not re.match(r'^09\d{9}$', phone) and not re.match(r'^۰۹[۰-۹]{۹}$', phone):
        await message.answer("❌ شماره موبایل نامعتبر است. لطفا دوباره تلاش کنید (مثال: 09123456789):")
        return

    await state.update_data(phone=phone)
    await state.set_state(OrderWizard.selecting_province)
    await message.answer("📍 استان خود را انتخاب کنید:", reply_markup=get_provinces_keyboard())

@router.callback_query(F.data.startswith("prov_page_"), OrderWizard.selecting_province)
async def province_pagination(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    await callback.message.edit_reply_markup(reply_markup=get_provinces_keyboard(page))
    await callback.answer()

@router.callback_query(F.data.startswith("prov_"), OrderWizard.selecting_province)
async def select_province(callback: CallbackQuery, state: FSMContext):
    province = callback.data.replace("prov_", "")
    await state.update_data(province=province)
    await state.set_state(OrderWizard.entering_city)
    await callback.message.answer(f"🏙 استان انتخاب شده: {province}\nحالا نام شهر خود را وارد کنید:")
    await callback.answer()

@router.message(OrderWizard.entering_city)
async def enter_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(OrderWizard.entering_address)
    await message.answer("🏠 آدرس دقیق پستی خود را وارد کنید:")

@router.message(OrderWizard.entering_address)
async def enter_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await state.set_state(OrderWizard.selecting_payment_method)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 کارت به کارت", callback_data="pay_card")],
        [InlineKeyboardButton(text="🌐 درگاه پرداخت آنلاین", callback_data="pay_gateway")] if settings.PAYMENT_GATEWAY_ENABLED else [],
        [InlineKeyboardButton(text="❌ لغو سفارش", callback_data="cancel_order")]
    ])

    await message.answer("💳 نحوه پرداخت را انتخاب کنید:", reply_markup=kb)

@router.callback_query(F.data.startswith("pay_"), OrderWizard.selecting_payment_method)
async def select_payment(callback: CallbackQuery, state: FSMContext):
    method = PaymentMethod.CARD_TO_CARD if callback.data == "pay_card" else PaymentMethod.GATEWAY
    await state.update_data(payment_method=method.value)

    data = await state.get_data()
    total_price = data['quantity'] * data['price']
    await state.update_data(total_price=total_price)

    summary = (
        "📋 <b>خلاصه سفارش شما:</b>\n\n"
        f"📦 محصول: {data['product_title']}\n"
        f"🔢 تعداد: {en_to_fa_digits(data['quantity'])}\n"
        f"👤 تحویل‌گیرنده: {data['full_name']}\n"
        f"📞 تلفن: {en_to_fa_digits(data['phone'])}\n"
        f"📍 آدرس: {data['province']}، {data['city']}، {data['address']}\n"
        f"💳 روش پرداخت: {'کارت به کارت' if method == PaymentMethod.CARD_TO_CARD else 'درگاه آنلاین'}\n"
        f"💰 <b>مبلغ کل: {format_price(total_price)}</b>\n\n"
        "آیا این اطلاعات مورد تایید است؟"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تایید و ثبت نهایی", callback_data="confirm_order")],
        [InlineKeyboardButton(text="❌ لغو و بازگشت", callback_data="cancel_order")]
    ])

    await state.set_state(OrderWizard.confirming_order)
    await callback.message.answer(summary, reply_markup=kb)
    await callback.answer()

import random
import string

def generate_order_code():
    return ''.join(random.choices(string.digits, k=6))

@router.callback_query(F.data == "confirm_order", OrderWizard.confirming_order)
async def confirm_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()

    # Get user
    result = await session.execute(select(User).where(User.telegram_user_id == callback.from_user.id))
    user = result.scalars().first()

    order_code = generate_order_code()

    order = Order(
        order_code=order_code,
        user_id=user.id,
        product_id=data['product_id'],
        quantity=data['quantity'],
        total_price=data['total_price'],
        status=OrderStatus.WAITING_PAYMENT,
        payment_method=PaymentMethod(data['payment_method']),
        address_json={
            "province": data['province'],
            "city": data['city'],
            "full_address": data['address']
        }
    )

    session.add(order)

    # Update product stock
    product = await session.get(Product, data['product_id'])
    product.stock -= data['quantity']

    await session.commit()

    if data['payment_method'] == PaymentMethod.CARD_TO_CARD.value:
        text = (
            f"✅ <b>سفارش شما با موفقیت ثبت شد!</b>\n"
            f"کد پیگیری سفارش: <code>{en_to_fa_digits(order_code)}</code>\n\n"
            f"💳 لطفاً مبلغ <b>{format_price(data['total_price'])}</b> را به کارت زیر واریز نمایید:\n\n"
            f"شماره کارت: <code>{en_to_fa_digits(settings.CARD_NUMBER)}</code>\n"
            f"به نام: {settings.CARD_OWNER_NAME}\n\n"
            "پس از واریز، لطفاً تصویر رسید یا شماره پیگیری را ارسال کنید."
        )
        await state.set_state(OrderWizard.awaiting_payment_receipt)
        await state.update_data(order_id=order.id)
        await callback.message.answer(text)
    else:
        # Gateway flow
        provider = MockGatewayProvider()
        payment_url = await provider.create_payment(order)

        text = (
            f"✅ <b>سفارش شما ثبت شد.</b>\n"
            f"کد پیگیری: <code>{en_to_fa_digits(order_code)}</code>\n\n"
            f"🔗 برای پرداخت آنلاین روی لینک زیر کلیک کنید:\n"
            f"{payment_url}"
        )
        await state.clear()
        await callback.message.answer(text, reply_markup=get_main_menu_keyboard())

    await callback.answer()

@router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ سفارش شما لغو شد.", reply_markup=get_main_menu_keyboard())
    await callback.answer()
