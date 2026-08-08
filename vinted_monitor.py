import os
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


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
    STATE_FILE.write_text(
        json.dumps(list(items), ensure_ascii=False)
    )


def get_items():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 900
            },
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        )

        page.goto(
            SEARCH_URL,
            wait_until="domcontentloaded",
            timeout=30000
        )

        page.wait_for_timeout(5000)

        items = page.locator('a[href*="/items/"]')
            """
            links => links.map(link => ({
                url: link.href,
                title: link.innerText.trim()
            }))
            """
        )

        browser.close()

    result = {}
    
    for item in items:
        if not item["url"]:
            continue

        if item["url"] in result:
            continue

        result[item["url"]] = {
            "url": item["url"],
            "title": item["title"] or "Vinted Artikel"
        }

    return list(result.values())


def send_discord(item):
    import requests

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

    current_ids = {
        item["url"]
        for item in items
    }

    # Beim ersten Durchlauf werden vorhandene Artikel
    # nur gespeichert und nicht als neue Treffer gemeldet.
    if not seen:
        save_seen(current_ids)
        print(
            f"Erster Durchlauf: "
            f"{len(items)} Artikel gespeichert."
        )
        return

    new_items = [
        item
        for item in items
        if item["url"] not in seen
    ]

    for item in new_items:
        print(f"Neuer Treffer: {item['url']}")
        send_discord(item)

    save_seen(seen | current_ids)

    print(
        f"Gefunden: {len(items)} | "
        f"Neu: {len(new_items)}"
    )


if __name__ == "__main__":
    main()
        
