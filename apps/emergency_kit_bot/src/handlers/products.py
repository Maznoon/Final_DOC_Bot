from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Product
from src.utils.text_utils import format_price, en_to_fa_digits
from src.config.config import settings

router = Router()

@router.message(F.text == "مشاهده مدل‌ها و قیمت")
async def list_products(message: Message, session: AsyncSession):
    result = await session.execute(select(Product).where(Product.is_active == True))
    products = result.scalars().all()

    if not products:
        await message.answer("در حال حاضر محصولی برای نمایش وجود ندارد.")
        return

    for product in products:
        text = (
            f"🏷 <b>{product.title_fa}</b>\n"
            f"💰 قیمت: {format_price(product.price_toman)}\n"
            f"📝 {product.description_fa[:100]}..."
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="مشاهده جزئیات و خرید", callback_data=f"product_{product.id}")]
        ])

        if product.image_url or settings.DEFAULT_PRODUCT_IMAGE:
            await message.answer_photo(
                photo=product.image_url or settings.DEFAULT_PRODUCT_IMAGE,
                caption=text,
                reply_markup=kb
            )
        else:
            await message.answer(text, reply_markup=kb)

@router.callback_query(F.data.startswith("product_"))
async def product_detail(callback: CallbackQuery, session: AsyncSession):
    product_id = int(callback.data.split("_")[1])
    product = await session.get(Product, product_id)

    if not product:
        await callback.answer("محصول یافت نشد.")
        return

    text = (
        f"🛡 <b>{product.title_fa}</b>\n\n"
        f"📄 <b>توضیحات:</b>\n{product.description_fa}\n\n"
        f"💰 <b>قیمت:</b> {format_price(product.price_toman)}\n"
        f"📦 <b>موجودی:</b> {en_to_fa_digits(product.stock)} عدد\n"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 خرید این مدل", callback_data=f"buy_{product.id}")],
        [InlineKeyboardButton(text="🔙 بازگشت به لیست", callback_data="list_products")]
    ])

    # Edit message text and keyboard if it was a photo message,
    # but since we might want to change image, maybe just send new one or edit caption.
    if callback.message.photo:
        await callback.message.edit_caption(caption=text, reply_markup=kb)
    else:
        await callback.message.edit_text(text=text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "list_products")
async def callback_list_products(callback: CallbackQuery, session: AsyncSession):
    await list_products(callback.message, session)
    await callback.message.delete()
    await callback.answer()
