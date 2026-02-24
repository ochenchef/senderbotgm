"""
Telegram Sender — основной скрипт рассылки
"""

import asyncio
import csv
import json
import os
import logging
from datetime import datetime, date
from telethon import TelegramClient
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, PeerFloodError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sender.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"
CONTACTS_FILE = "contacts.csv"
PROGRESS_FILE = "progress.json"


def load_config():
    """Загрузка конфига или запрос при первом запуске"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, encoding='utf-8') as f:
            return json.load(f)
    return None


def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_contacts():
    contacts = []
    if not os.path.exists(CONTACTS_FILE):
        return contacts
    with open(CONTACTS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            contact = {
                'phone': row.get('phone', '').strip(),
                'username': row.get('username', '').strip(),
                'name': row.get('name', '').strip(),
            }
            if contact['phone'] or contact['username']:
                contacts.append(contact)
    return contacts


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {
        "sent_today": 0,
        "last_date": None,
        "total_sent": 0,
        "sent_contacts": [],
        "failed_contacts": []
    }


def save_progress(progress):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def get_pending_contacts(contacts, progress):
    sent_ids = set(progress.get("sent_contacts", []))
    failed_ids = set(progress.get("failed_contacts", []))
    done = sent_ids | failed_ids
    return [c for c in contacts if (c['phone'] or c['username']) not in done]


async def send_to_contact(client, contact, message, attachment=None):
    identifier = contact['phone'] or f"@{contact['username'].lstrip('@')}"
    name = contact.get('name', identifier)

    try:
        personal_message = message.replace("{name}", contact['name']) if contact.get('name') else message

        if attachment and os.path.exists(attachment):
            await client.send_file(identifier, attachment, caption=personal_message)
        else:
            await client.send_message(identifier, personal_message)

        logger.info(f"✅ Отправлено: {name} ({identifier})")
        return True

    except FloodWaitError as e:
        logger.warning(f"⏳ FloodWait {e.seconds} сек. Ждём...")
        await asyncio.sleep(e.seconds + 10)
        return False
    except UserPrivacyRestrictedError:
        logger.warning(f"🔒 {name}: закрытые настройки приватности, пропускаем")
        return None
    except PeerFloodError:
        logger.error("🚨 Telegram заблокировал рассылку (PeerFlood). Остановка.")
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка для {name} ({identifier}): {e}")
        return None


async def run_sender(config):
    contacts = load_contacts()
    if not contacts:
        logger.error("Нет контактов! Добавь их через веб-интерфейс.")
        return

    progress = load_progress()

    today = str(date.today())
    if progress.get("last_date") != today:
        progress["sent_today"] = 0
        progress["last_date"] = today
        logger.info("🌅 Новый день, счётчик сброшен")

    pending = get_pending_contacts(contacts, progress)
    if not pending:
        logger.info("✨ Все контакты обработаны!")
        return

    daily_limit = config.get("daily_limit", 25)
    batch_size = config.get("batch_size", 5)
    pause_between_batches = config.get("pause_minutes", 5) * 60
    pause_between_messages = config.get("pause_seconds", 10)
    message = config.get("message", "Привет!")
    attachment = config.get("attachment_file", "")

    can_send_today = daily_limit - progress["sent_today"]
    if can_send_today <= 0:
        logger.info(f"📊 Дневной лимит ({daily_limit}) достигнут.")
        return

    to_send = pending[:can_send_today]
    logger.info(f"📬 Отправляем: {len(to_send)} контактов")

    async with TelegramClient(
        config.get("session_name", "my_session"),
        config["api_id"],
        config["api_hash"]
    ) as client:
        await client.start()
        logger.info("🔐 Авторизован в Telegram")

        i = 0
        batch_num = 0

        while i < len(to_send):
            batch = to_send[i:i + batch_size]
            batch_num += 1
            logger.info(f"\n📦 Пачка {batch_num}: {len(batch)} контактов")

            for contact in batch:
                try:
                    result = await send_to_contact(
                        client, contact, message,
                        attachment if attachment else None
                    )
                    identifier = contact['phone'] or contact['username']

                    if result is True:
                        progress["sent_contacts"].append(identifier)
                        progress["total_sent"] += 1
                        progress["sent_today"] += 1
                    elif result is None:
                        progress["failed_contacts"].append(identifier)

                    save_progress(progress)
                    await asyncio.sleep(pause_between_messages)

                except PeerFloodError:
                    logger.error("🛑 Остановка из-за блокировки Telegram")
                    return

            i += batch_size
            if i < len(to_send):
                logger.info(f"⏸️ Пауза {pause_between_batches // 60} мин...")
                await asyncio.sleep(pause_between_batches)

    logger.info(f"\n✅ Готово! Сегодня: {progress['sent_today']}, всего: {progress['total_sent']}")


if __name__ == "__main__":
    config = load_config()
    if not config:
        print("Конфиг не найден. Запусти веб-интерфейс: python web_interface.py")
    else:
        asyncio.run(run_sender(config))
