def en_to_fa_digits(text: str) -> str:
    if text is None:
        return ""
    en_digits = "0123456789"
    fa_digits = "۰۱۲۳۴۵۶۷۸۹"
    translation_table = str.maketrans(en_digits, fa_digits)
    return str(text).translate(translation_table)

def format_price(price: int) -> str:
    formatted = "{:,}".format(price)
    return f"{en_to_fa_digits(formatted)} تومان"

def rtl_text(text: str) -> str:
    # Basic RTL support: append a special character or just return text
    # Usually Telegram handles RTL automatically if the first character is RTL.
    return text

def get_status_label(status_value: str) -> str:
    status_map = {
        "NEW": "جدید",
        "WAITING_PAYMENT": "در انتظار پرداخت",
        "PENDING_REVIEW": "در انتظار بررسی رسید",
        "PAID": "پرداخت شده / آماده‌سازی",
        "PACKING": "در حال بسته‌بندی",
        "SHIPPED": "ارسال شده",
        "DELIVERED": "تحویل داده شده",
        "CANCELED": "لغو شده"
    }
    return status_map.get(status_value, status_value)
