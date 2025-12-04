# bot/handlers/qa_states.py - ОБНОВЛЕННАЯ ВЕРСИЯ
from aiogram.fsm.state import State, StatesGroup


class QAStates(StatesGroup):
    waiting_for_question = State()
    waiting_for_answer = State()
    viewing_questions = State()
    waiting_for_photo_request = State()


class UserQAStates(StatesGroup):
    waiting_for_question = State()
    in_dialog = State()
    waiting_for_clarification = State()
    waiting_for_prescription_photo = State() 
