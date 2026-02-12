from aiogram.fsm.state import State, StatesGroup

class OrderWizard(StatesGroup):
    selecting_quantity = State()
    entering_name = State()
    entering_phone = State()
    selecting_province = State()
    entering_city = State()
    entering_address = State()
    selecting_payment_method = State()
    confirming_order = State()
    awaiting_payment_receipt = State()
