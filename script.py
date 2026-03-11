import asyncio
import hashlib
import json
import logging
import os
import re
import sys
import time

from dotenv import load_dotenv
from telethon import TelegramClient, events


load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


api_id = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")
phone_number = os.getenv("TELEGRAM_PHONE_NUMBER")

if not all([api_id, api_hash, phone_number]):
    logger.error(
        "Missing required environment variables. Set TELEGRAM_API_ID, "
        "TELEGRAM_API_HASH, and TELEGRAM_PHONE_NUMBER in .env."
    )
    sys.exit(1)

try:
    api_id = int(api_id)
except (TypeError, ValueError):
    logger.error("TELEGRAM_API_ID must be a valid integer.")
    sys.exit(1)


SOURCE_CHANNELS_FILE = "source_channels.txt"
SOURCE_TOPICS_FILE = "source_topics.txt"
TARGET_CHATS_FILE = "target_chats.txt"
REGEX_FILTERS_FILE = "regex_filters.txt"
PROCESSED_ITEMS_FILE = "processed_items.json"


def read_entries_from_file(file_path):
    entries = []
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            for raw_line in file:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    entries.append(int(line))
                except ValueError:
                    entries.append(line)
        if not entries:
            logger.error(f"No valid entries found in {file_path}")
        return entries
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []
    except Exception as exc:
        logger.error(f"Error reading {file_path}: {exc}")
        return []


def read_source_topics(file_path):
    if not os.path.exists(file_path):
        logger.info(
            f"Topic filter file not found: {file_path}. Listening to all messages."
        )
        return {}

    topics = {}
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            for raw_line in file:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                if line.startswith("https://t.me/"):
                    match = re.match(r"https://t\.me/c/(\d+)/(\d+)", line)
                    if not match:
                        logger.warning(f"Invalid topic link: {line}")
                        continue
                    chat_id = f"-100{match.group(1)}"
                    topic_id = int(match.group(2))
                else:
                    try:
                        chat_id, topic_id = line.split(":", 1)
                        chat_id = chat_id.strip()
                        topic_id = int(topic_id.strip())
                    except ValueError:
                        logger.warning(f"Invalid topic entry in {file_path}: {line}")
                        continue

                topics.setdefault(chat_id, []).append(topic_id)
        return topics
    except Exception as exc:
        logger.error(f"Error reading {file_path}: {exc}")
        return {}


def load_regex_filters(file_path):
    if not os.path.exists(file_path):
        logger.info(f"Regex filter file not found: {file_path}. Routing all messages.")
        return []

    compiled_patterns = []
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            for line_number, raw_line in enumerate(file, start=1):
                pattern = raw_line.strip()
                if not pattern or pattern.startswith("#"):
                    continue
                try:
                    compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error as exc:
                    logger.warning(
                        f"Invalid regex in {file_path} at line {line_number}: {exc}"
                    )
        logger.info(f"Loaded {len(compiled_patterns)} regex filter(s).")
        return compiled_patterns
    except Exception as exc:
        logger.error(f"Error reading {file_path}: {exc}")
        return []


def load_processed_items():
    try:
        with open(PROCESSED_ITEMS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as exc:
        logger.error(f"Error loading {PROCESSED_ITEMS_FILE}: {exc}")
        return {}


def save_processed_items(items):
    try:
        with open(PROCESSED_ITEMS_FILE, "w", encoding="utf-8") as file:
            json.dump(items, file, indent=2)
    except Exception as exc:
        logger.error(f"Error saving {PROCESSED_ITEMS_FILE}: {exc}")


def build_message_fingerprint(text):
    normalized_text = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()[:24]


def build_route_key(source_chat_id, message_id, message_text):
    fingerprint = build_message_fingerprint(message_text)
    return f"{source_chat_id}:{message_id}:{fingerprint}"


def message_matches_filters(text, compiled_patterns):
    if not text or not text.strip():
        return False, []

    if not compiled_patterns:
        return True, []

    matched_patterns = []
    for pattern in compiled_patterns:
        if pattern.search(text):
            matched_patterns.append(pattern.pattern)

    return bool(matched_patterns), matched_patterns


def transform_message(text):
    return text.strip()


source_channels = read_entries_from_file(SOURCE_CHANNELS_FILE)
source_topics = read_source_topics(SOURCE_TOPICS_FILE)
target_chats = read_entries_from_file(TARGET_CHATS_FILE)
regex_filters = load_regex_filters(REGEX_FILTERS_FILE)

if not source_channels:
    logger.error(f"No source channels loaded. Check {SOURCE_CHANNELS_FILE}.")
    sys.exit(1)

if not target_chats:
    logger.error(f"No target chats loaded. Check {TARGET_CHATS_FILE}.")
    sys.exit(1)


client = TelegramClient("session", api_id, api_hash)
processed_items = load_processed_items()


async def resolve_entity(entry):
    try:
        return await client.get_entity(entry)
    except Exception:
        if not isinstance(entry, str):
            raise

    normalized_entry = entry.strip().lstrip("@").lower()
    async for dialog in client.iter_dialogs():
        dialog_name = (dialog.name or "").strip().lower()
        dialog_username = getattr(dialog.entity, "username", None)
        if dialog_name == normalized_entry:
            return dialog.entity
        if dialog_username and dialog_username.lower() == normalized_entry:
            return dialog.entity

    raise ValueError(f"Could not resolve chat/channel/bot: {entry}")


async def main():
    await client.start(phone=phone_number)
    logger.info("Client connected.")

    if not await client.is_user_authorized():
        logger.error("User not authorized. Complete the Telegram login process.")
        return

    resolved_source_channels = []
    for channel in source_channels:
        try:
            resolved_source_channels.append(await resolve_entity(channel))
            logger.info(f"Verified access to source entity: {channel}")
        except Exception as exc:
            logger.error(f"Cannot access source entity {channel}: {exc}")

    resolved_target_chats = []
    for chat in target_chats:
        try:
            resolved_target_chats.append(await resolve_entity(chat))
            logger.info(f"Verified access to target entity: {chat}")
        except Exception as exc:
            logger.error(f"Cannot access target entity {chat}: {exc}")

    if not resolved_source_channels:
        logger.error("No accessible source entities were resolved.")
        return

    if not resolved_target_chats:
        logger.error("No accessible target entities were resolved.")
        return

    @client.on(events.NewMessage(chats=resolved_source_channels))
    async def handler(event):
        message = event.message
        message_text = message.text or ""
        chat = await event.get_chat()
        source_chat_id = str(getattr(chat, "id", "unknown"))
        topic_id = getattr(message, "reply_to_top_msg_id", None) or getattr(
            message, "reply_to_msg_id", None
        )

        if source_chat_id in source_topics:
            if topic_id is None or topic_id not in source_topics[source_chat_id]:
                logger.info(
                    f"Skipped message from {source_chat_id} because topic {topic_id} is not allowed."
                )
                return

        logger.info(
            f"Received message from {source_chat_id} (topic {topic_id}): {message_text[:80]}"
        )

        matches_filter, matched_patterns = message_matches_filters(
            message_text, regex_filters
        )
        if not matches_filter:
            logger.info("Skipped message because no regex filters matched.")
            return

        transformed_text = transform_message(message_text)
        route_key = build_route_key(source_chat_id, message.id, transformed_text)

        global processed_items
        if route_key in processed_items:
            logger.info(f"Skipped previously routed item {route_key}.")
            return

        processed_items[route_key] = {
            "source_chat_id": source_chat_id,
            "message_id": message.id,
            "timestamp": time.time(),
            "matched_patterns": matched_patterns,
        }
        save_processed_items(processed_items)

        logger.info(
            f"Routing matched message to {len(resolved_target_chats)} target entities."
        )

        for target_chat in resolved_target_chats:
            try:
                await client.send_message(target_chat, transformed_text)
                logger.info(
                    "Sent message to %s",
                    getattr(
                        target_chat,
                        "title",
                        getattr(target_chat, "username", target_chat),
                    ),
                )
            except Exception as exc:
                logger.error(f"Failed to send message to {target_chat}: {exc}")

    logger.info("Router is running and listening for new messages.")
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Script stopped by user.")
    except Exception as exc:
        logger.error(f"Script failed: {exc}")
