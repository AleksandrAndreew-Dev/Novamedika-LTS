
from aiogram.fsm.state import State, StatesGroup


class QAStates(StatesGroup):
    waiting_for_question = State()
    waiting_for_answer = State()
    viewing_questions = State()
    waiting_for_photo_request = State()
    in_dialog_with_user = State()

class UserQAStates(StatesGroup):
    waiting_for_question = State()
    in_dialog = State()  # Уже есть
    waiting_for_clarification = State()
    waiting_for_prescription_photo = State()
