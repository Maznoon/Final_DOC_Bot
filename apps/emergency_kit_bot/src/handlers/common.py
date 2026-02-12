from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.utils.keyboard_utils import get_main_menu_keyboard
from src.services.user_service import get_or_create_user
from src.utils.text_utils import en_to_fa_digits, format_price, get_status_label
from src.db.models import Order, Product

router = Router()

class TrackingState(StatesGroup):
    waiting_for_code = State()

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    user = await get_or_create_user(
        session,
        message.from_user.id,
        message.from_user.full_name
    )

    welcome_text = (
        "سلام! به فروشگاه کیت آمادگی بحران شهری خوش آمدید. 🛡\n\n"
        "هدف ما کمک به شما برای آمادگی در برابر شرایط اضطراری و بحران‌های شهری است. "
        "با داشتن کیت‌های ۷۲ ساعته ما، خیالتان از بابت نیازهای اولیه در زمان بحران راحت خواهد بود.\n\n"
        "لطفاً از منوی زیر یکی از گزینه‌ها را انتخاب کنید:"
    )

    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard())

@router.message(F.text == "معرفی کیت")
async def about_kit(message: Message):
    about_text = (
        "📦 <b>کیت آمادگی بحران ۷۲ ساعته چیست؟</b>\n\n"
        "این کیت مجموعه‌ای از اقلام ضروری (خوراک، بهداشت، کمک‌های اولیه و ابزار) است که برای زنده ماندن "
        "و حفظ ایمنی یک نفر به مدت ۳ روز در شرایط بحرانی طراحی شده است.\n\n"
        "✅ <b>مزایا:</b>\n"
        "- سبک و قابل حمل\n"
        "- تاریخ انقضای طولانی اقلام\n"
        "- مطابق با استانداردهای مدیریت بحران\n\n"
        "شما می‌توانید با انتخاب مدل‌های مختلف، سطح آمادگی خود را ارتقا دهید."
    )
    await message.answer(about_text)

@router.message(F.text == "سوالات متداول")
async def faq(message: Message):
    faq_text = (
        "❓ <b>سوالات متداول</b>\n\n"
        "<b>۱. تحویل سفارش چقدر زمان می‌برد؟</b>\n"
        "معمولاً بین ۲ تا ۴ روز کاری.\n\n"
        "<b>۲. آیا امکان مرجوعی وجود دارد؟</b>\n"
        "بله، در صورت نقص فنی یا باز نشدن پلمب کیت تا ۷ روز.\n\n"
        "<b>۳. تاریخ انقضای محصولات چقدر است؟</b>\n"
        "تمامی اقلام خوراکی و دارویی دارای حداقل ۱ سال تاریخ انقضا هستند."
    )
    await message.answer(faq_text)

@router.message(F.text == "پیگیری سفارش")
async def track_order_start(message: Message, state: FSMContext):
    await state.set_state(TrackingState.waiting_for_code)
    await message.answer("🔍 لطفاً کد پیگیری ۶ رقمی سفارش خود را وارد کنید:")

@router.message(TrackingState.waiting_for_code)
async def track_order_result(message: Message, state: FSMContext, session: AsyncSession):
    code = message.text
    # Convert Persian digits to English for DB lookup
    en_code = "".join([str("۰۱۲۳۴۵۶۷۸۹".find(c)) if c in "۰۱۲۳۴۵۶۷۸۹" else c for c in code])

    result = await session.execute(select(Order).where(Order.order_code == en_code))
    order = result.scalars().first()

    if not order:
        await message.answer("❌ سفارش با این کد یافت نشد. لطفاً دوباره تلاش کنید یا به منوی اصلی برگردید.")
        return

    product = await session.get(Product, order.product_id)

    text = (
        f"📦 <b>وضعیت سفارش {en_to_fa_digits(order.order_code)}</b>\n\n"
        f"🛍 محصول: {product.title_fa}\n"
        f"💰 مبلغ: {format_price(order.total_price)}\n"
        f"📊 وضعیت فعلی: <b>{get_status_label(order.status.value)}</b>\n"
    )

    if order.shipping_tracking_code:
        text += f"🚚 کد رهگیری پستی: <code>{en_to_fa_digits(order.shipping_tracking_code)}</code>"

    await message.answer(text, reply_markup=get_main_menu_keyboard())
    await state.clear()

@router.message(F.text == "بازگشت به منوی اصلی")
async def back_to_main(message: Message):
    await message.answer("منوی اصلی:", reply_markup=get_main_menu_keyboard())
