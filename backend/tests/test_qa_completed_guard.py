import asyncio
import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException

os.environ.setdefault("SECRET_KEY", "test-secret-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from routers.qa import (  # noqa: E402
    MessageCreate,
    PublicMessageCreate,
    send_consultation_message,
    send_public_question_message,
)


class _FakeResult:
    def __init__(self, obj):
        self._obj = obj

    def scalar_one_or_none(self):
        return self._obj


class _FakeDB:
    """Минимальный stub сессии: возвращает заданный Question на первый запрос."""

    def __init__(self, question):
        self._question = question
        self.committed = False

    async def execute(self, *args, **kwargs):
        return _FakeResult(self._question)

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass


def _completed_question():
    return type(
        "QuestionStub",
        (),
        {"uuid": uuid.uuid4(), "status": "completed", "user_id": uuid.uuid4()},
    )()


def _user():
    return type("UserStub", (), {"uuid": uuid.uuid4()})()


def test_send_consultation_message_rejects_completed_dialog():
    """Завершённая консультация не переоткрывается: 409 consultation_completed."""
    question = _completed_question()
    db = _FakeDB(question)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            send_consultation_message(
                consultation_id=str(question.uuid),
                message=MessageCreate(text="сообщение после завершения"),
                current_user=_user(),
                db=db,
            )
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "consultation_completed"
    # Диалог не должен быть переоткрыт (commit не выполнялся)
    assert db.committed is False


def test_send_public_question_message_rejects_completed_dialog():
    """Анонимный (public) эндпоинт тоже не переоткрывает завершённый диалог."""
    question = _completed_question()
    db = _FakeDB(question)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            send_public_question_message(
                question_id=str(question.uuid),
                message=PublicMessageCreate(text="сообщение после завершения"),
                request=None,
                db=db,
            )
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "consultation_completed"
    assert db.committed is False
