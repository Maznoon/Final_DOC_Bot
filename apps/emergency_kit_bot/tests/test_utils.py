from src.utils.text_utils import en_to_fa_digits, format_price

def test_en_to_fa_digits():
    assert en_to_fa_digits("1234567890") == "۱۲۳۴۵۶۷۸۹۰"
    assert en_to_fa_digits("Order 123") == "Order ۱۲۳"
    assert en_to_fa_digits(None) == ""

def test_format_price():
    assert format_price(1500000) == "۱,۵۰۰,۰۰۰ تومان"
    assert format_price(2500000) == "۲,۵۰۰,۰۰۰ تومان"
