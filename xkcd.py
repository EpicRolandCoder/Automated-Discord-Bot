import requests
import random

def get_random_xkcd():
    latest = requests.get("https://xkcd.com/info.0.json", timeout=10)
    latest.raise_for_status()
    latest_data = latest.json()
    max_num = latest_data.get("num", 0)
    if max_num <= 0:
        return None
    rand = random.randint(1, max_num)
    resp = requests.get(f"https://xkcd.com/{rand}/info.0.json", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return {
        "num": data.get("num"),
        "title": data.get("title"),
        "img": data.get("img"),
        "alt": data.get("alt"),
        "link": f"https://xkcd.com/{data.get('num')}/"
    }
