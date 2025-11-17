# bot/handlers/qa_states.py
from aiogram.fsm.state import State, StatesGroup

class QAStates(StatesGroup):
    waiting_for_question = State()
    waiting_for_answer = State()
    viewing_questions = State()
