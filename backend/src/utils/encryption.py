"""Утилиты для шифрования персональных данных согласно требованиям ОАЦ."""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


def get_encryption_key() -> bytes:
    """
    Получить ключ шифрования из环境 переменной ENCRYPTION_KEY.
    Если ключ не задан, генерирует новый (только для разработки!).
    
    Returns:
        bytes: 32-байтовый ключ для Fernet
    """
    encryption_key_env = os.getenv("ENCRYPTION_KEY")
    
    if not encryption_key_env:
        # ВНИМАНИЕ: В production это должно вызывать ошибку!
        logger.warning(
            "ENCRYPTION_KEY не установлен! Генерируется временный ключ. "
            "Это НЕ безопасно для production!"
        )
        # Генерируем ключ из фиксированного seed для консистентности в dev
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"novamedika-dev-salt",  # Только для разработки!
            iterations=480000,
        )
        return kdf.derive(b"dev-key-material")
    
    # Преобразуем base64-encoded ключ в bytes
    try:
        if len(encryption_key_env) == 44:  # base64-encoded 32-byte key
            return base64.urlsafe_b64decode(encryption_key_env)
        else:
            # Предполагаем, что это raw key
            key_bytes = encryption_key_env.encode() if isinstance(encryption_key_env, str) else encryption_key_env
            if len(key_bytes) != 32:
                raise ValueError(f"Ключ должен быть 32 байта, получено {len(key_bytes)}")
            return base64.urlsafe_b64encode(key_bytes)
    except Exception as e:
        logger.error(f"Ошибка при обработке ENCRYPTION_KEY: {e}")
        raise


def get_fernet_cipher() -> Fernet:
    """
    Создать экземпляр Fernet cipher с ключом из environment переменной.
    
    Returns:
        Fernet: Экземпляр шифра
    """
    # Получаем уже декодированный 32-байтовый ключ
    key_bytes = get_encryption_key()
    
    # Fernet ожидает URL-safe base64-encoded ключ (строку или bytes в base64 формате)
    # Но get_encryption_key() уже возвращает decoded bytes, поэтому нужно перекодировать обратно
    key_b64 = base64.urlsafe_b64encode(key_bytes)
    return Fernet(key_b64)


def encrypt_value(value: str) -> str:
    """
    Зашифровать строковое значение.
    
    Args:
        value: Исходное значение
        
    Returns:
        str: Base64-encoded зашифрованное значение
    """
    if value is None:
        return None
    
    try:
        cipher = get_fernet_cipher()
        encrypted_bytes = cipher.encrypt(value.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Ошибка шифрования: {e}")
        raise


def decrypt_value(encrypted_value: str) -> str:
    """
    Расшифровать значение.
    
    Args:
        encrypted_value: Base64-encoded зашифрованное значение
        
    Returns:
        str: Расшифрованное значение
    """
    if encrypted_value is None:
        return None
    
    try:
        cipher = get_fernet_cipher()
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode('utf-8'))
        decrypted_bytes = cipher.decrypt(encrypted_bytes)
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"Ошибка дешифрования: {e}")
        raise


def encrypt_bigint(value: int) -> str:
    """
    Зашифровать BigInt значение (например, telegram_id).
    
    Args:
        value: Целочисленное значение
        
    Returns:
        str: Base64-encoded зашифрованное значение
    """
    if value is None:
        return None
    
    return encrypt_value(str(value))


def decrypt_bigint(encrypted_value: str) -> int:
    """
    Расшифровать BigInt значение.
    
    Args:
        encrypted_value: Base64-encoded зашифрованное значение
        
    Returns:
        int: Расшифрованное целочисленное значение
    """
    if encrypted_value is None:
        return None
    
    decrypted_str = decrypt_value(encrypted_value)
    return int(decrypted_str)
