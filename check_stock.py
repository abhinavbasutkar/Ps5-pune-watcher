import requests
from bs4 import BeautifulSoup
import json
import os
import re

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = "state.json"

STORES = {
    "Amazon": {
        "url": "https://www.amazon.in/s?k=playstation+5",
        "out_of_stock_hints": ["currently unavailable", "out of stock"],
    },
    "Flipkart": {
        "url": "https://www.flipkart.com/search?q=playstation%205",
        "out_of_stock_hints": ["sold out", "notify me"],
    },
    "Croma": {
        "url": "https://www.croma.com/searchB?q=playstation%205",
        "out_of_stock_hints": ["out of stock", "notify me"],
    },
    "Reliance Digital": {
        "url": "https://www.reliancedigital.in/collection/sony-ps5-consoles",
        "out_of_stock_hints": ["out of stock", "notify me"],
    },
    "Vijay Sales": {
        "url": "https://www.vijaysales.com/search?text=ps5",
        "out_of_stock_hints": ["out of stock", "notify me"],
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(
            url,
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
    except Exception as e:
        print(f"Telegram send failed: {e}")


def get_visible_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).lower()


def check_store(name, cfg, state):
    try:
        resp = requests.get(cfg["url"], headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"[{name}] fetch failed: {e}")
        return

    text = get_visible_text(resp.text)
    was_out = state.get(name, {}).get("out_of_stock", True)
    now_out = any(hint in text for hint in cfg["out_of_stock_hints"])

    if was_out and not now_out:
        send_telegram(
            f"POSSIBLE RESTOCK: {name}\n{cfg['url']}\n\n"
            f"This is a heuristic guess based on page text — verify on the "
            f"page immediately, it can be wrong."
        )
        print(f"[{name}] ALERT sent")
    else:
        print(f"[{name}] no change (out_of_stock={now_out})")

    state[name] = {"out_of_stock": now_out}


def main():
    state = load_state()
    for name, cfg in STORES.items():
        check_store(name, cfg, state)
    save_state(state)


if __name__ == "__main__":
    main()
