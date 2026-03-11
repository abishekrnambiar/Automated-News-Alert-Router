# Automated News & Alert Router

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Telethon](https://img.shields.io/badge/Telethon-Telegram%20Automation-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://github.com/LonamiWebs/Telethon)
[![AsyncIO](https://img.shields.io/badge/AsyncIO-Real--Time%20Processing-222222?style=for-the-badge)](https://docs.python.org/3/library/asyncio.html)
[![Regex](https://img.shields.io/badge/Regex-Advanced%20Filtering-0F766E?style=for-the-badge)](https://docs.python.org/3/library/re.html)

A professional-grade automation engine built with Telethon. Seamlessly routes messages between channels, groups, private chats, and bots with advanced regex filtering and asynchronous processing.

## Key Highlights

- Supports Telegram channels, groups, private chats, and bot dialogs using chat IDs, usernames, links, or resolvable dialog titles.
- Implements intelligent regex keyword matching for precise content filtering.
- Built on an asynchronous core for low-latency, real-time message handling.
- Modular design allowing easy integration of custom routing, mirroring, or transformation logic.
- Persists processed route state to avoid duplicate forwarding.
- Supports optional topic-based filtering for forum/supergroup topics.

## Tech Stack

- Python
- Telethon
- AsyncIO
- Regex
- JSON

## Challenge

Real-time sync, session persistence, private entity access, and efficient filtering across multiple Telegram sources.

## Use Case

Content Aggregation & Mirroring: Centralizes signals, alerts, or news from multiple private Telegram sources into a single master group or multiple target destinations for efficient monitoring.

## Project Structure

```text
Automated-News-Alert-Router/
|-- script.py
|-- README.md
|-- requirements.txt
|-- source_channels.txt
|-- target_chats.txt
|-- regex_filters.txt
|-- processed_items.json
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create your `.env` file

This project does not include your private `.env` file in Git. Create a `.env` file in the project root with:

```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE_NUMBER=your_phone_number
```

### 3. Configure source entities

Add the Telegram sources you want to monitor in `source_channels.txt`.

Supported source types:

- Public channels
- Private channels you already have access to
- Public groups and supergroups
- Private groups available in your Telegram session
- Private chats/dialogs
- Bot dialogs

Examples:

```text
# private/public entity by chat ID
-1001234567890

# public username
@PublicNewsChannel
```

### 4. Configure target entities

Add the destinations you want to route messages to in `target_chats.txt`.

Examples:

```text
# master group by chat ID
-1009876543210

# public username
@MyTargetGroup
```

### 5. Configure regex filters

Add one regex pattern per line in `regex_filters.txt`.

Examples:

```text
breaking\s+news
alert
signal
important\s+update
listing
partnership
```

Behavior:

- If at least one regex matches, the message is routed.
- If no regex matches, the message is skipped.
- If `regex_filters.txt` is empty or missing, all incoming messages are routed.

### 6. Run the router

```bash
python script.py
```

On first run, Telethon may prompt for OTP/login confirmation and will generate a local session file.

## How It Works

1. Loads Telegram credentials from `.env`.
2. Starts a Telethon client and restores your session.
3. Resolves source and target entries from IDs, usernames, links, or dialog titles.
4. Watches all configured sources in real time.
5. Optionally restricts routing to configured topics.
6. Applies regex keyword matching to every incoming message.
7. Deduplicates routed messages using `processed_items.json`.
8. Forwards matched messages to every configured target entity.

## Duplicate Handling

The router stores processed route metadata in `processed_items.json` using:

- source chat ID
- Telegram message ID
- normalized message fingerprint

This prevents the same source message from being routed repeatedly.

## Notes

- `regex_filters.txt` is optional but recommended for selective routing.
- The bot uses your Telegram session, so it can work with private sources and private targets you already have access to.
- `.env`, session files, and Python cache files are already excluded by `.gitignore`.
- Replace the sample entries in `source_channels.txt` and `target_chats.txt` with your own real Telegram entities before running.
- Keep `processed_items.json` empty in the public repo unless you intentionally want to publish routed message metadata.

## License

No license file is included by default. If you want others to reuse this publicly, add a license such as MIT.
