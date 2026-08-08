import os
import json
import hashlib
from pathlib import Path

import requests
from bs4 import BeautifulSoup


SEARCH_URL = os.environ["VINTED_SEARCH_URL"]
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

STATE_FILE = Path("seen_items.json")


def load_seen():
    if not STATE_FILE.exists():
        return set()

    try:
        return set(json.loads(STATE_FILE.read_text()))
    except Exception:
        return set()


def save_seen(items):
    STATE_FILE.write_text(json.dumps(list(items)))


def get_items():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        SEARCH_URL,
        headers=headers,
        timeout=20
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    items = []

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if "/items/" not in href:
            continue

        title = link.get_text(" ", strip=True)

        if not title:
            continue

        if href.startswith("/"):
            href = "https://www.vinted.de" + href

        item_id = hashlib.sha256(href.encode()).hexdigest()

        items.append({
            "id": item_id,
            "title": title,
            "url": href
        })

    unique = {}
    for item in items:
        unique[item["id"]] = item

    return list(unique.values())


def send_discord(item):
    message = {
        "content": (
            "🚨 **NEUER VINTED-TREFFER**\n\n"
            f"**{item['title']}**\n"
            f"🔗 {item['url']}"
        )
    }

    response = requests.post(
        DISCORD_WEBHOOK,
        json=message,
        timeout=20
    )
    response.raise_for_status()


def main():
    seen = load_seen()
    items = get_items()

    current_ids = {item["id"] for item in items}

    new_items = [
        item for item in items
        if item["id"] not in seen
    ]

    # Beim ersten Lauf nichts spammen:
    # Die vorhandenen Artikel werden nur gespeichert.
    if not seen:
        save_seen(current_ids)
        print(f"Erster Lauf: {len(items)} Artikel gespeichert.")
        return

    for item in new_items:
        send_discord(item)
        print(f"Neuer Treffer: {item['url']}")

    save_seen(seen | current_ids)


if __name__ == "__main__":
    main()
