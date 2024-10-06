from aiogram.fsm.state import StatesGroup, State

class InputState(StatesGroup):
    waiting_for_category_name = State()
    waiting_for_category_deletion = State()
    waiting_for_category_update = State()
    waiting_for_task_description = State()
    waiting_for_new_category_name = State()
    waiting_for_reminder_input = State()