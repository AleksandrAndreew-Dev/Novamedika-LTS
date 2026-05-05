# db/__init__.py
from .base import Base
from .models import Pharmacy, Product
from .booking_models import BookingOrder, PharmacyAPIConfig, SyncLog
from .qa_models import User, Pharmacist, Question, Answer

# Импорт event listeners для автоматического шифрования персональных данных
# Этот импорт регистрирует SQLAlchemy events при загрузке приложения
from . import encryption_events

__all__ = [
    'Base',
    'Pharmacy',
    'Product',
    'BookingOrder',
    'PharmacyAPIConfig',
    'SyncLog',
    'User',
    'Pharmacist',
    'Question',
    'Answer'
]
