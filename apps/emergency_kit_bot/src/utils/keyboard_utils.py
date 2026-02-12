from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def get_main_menu_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="معرفی کیت"), KeyboardButton(text="مشاهده مدل‌ها و قیمت"))
    builder.row(KeyboardButton(text="ثبت سفارش"), KeyboardButton(text="پیگیری سفارش"))
    builder.row(KeyboardButton(text="سوالات متداول"), KeyboardButton(text="ارتباط با پشتیبانی"))
    return builder.as_markup(resize_keyboard=True)

def get_back_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="بازگشت به منوی اصلی"))
    return builder.as_markup(resize_keyboard=True)
