import httpx
import logging
import os


logger = logging.getLogger(__name__)


async def send_a1_sms(phone: str, text: str):
    """Отправка SMS через API A1"""
    # Очистка номера телефона: должен начинаться с 375
    clean_phone = "".join(filter(str.isdigit, phone))
    if clean_phone.startswith("80"):  # замена локального формата на международный
        clean_phone = "375" + clean_phone[2:]
    elif clean_phone.startswith("7"):  # если вдруг РФ, но А1 работает с +375
        pass

    url = "https://smart-sender.a1.by/api/send/sms"
    params = {
        "user": os.getenv("a1User"),  # Из настроек
        "apikey": os.getenv("a1apk"),  # Из настроек
        "msisdn": clean_phone,
        "text": text,
        "sender": "Novamedika",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            result = response.json()
            if result.get("status"):
                logger.info(
                    f"SMS sent to {clean_phone}, ID: {result.get('message_id')}"
                )
            else:
                logger.error(f"A1 SMS Error: {result.get('error')}")
    except Exception as e:
        logger.error(f"Failed to connect to A1 API: {e}")
