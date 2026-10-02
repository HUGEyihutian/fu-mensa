#!/usr/bin/env python3
"""Fetch this week's and next week's menus for all FU Berlin canteens
directly from the official studierendenWERK BERLIN website (stw.berlin)
and write them to docs/data/menus.json.

Source: the same endpoint the official site uses for its day tabs:
POST https://www.stw.berlin/xhr/speiseplan-wochentag.html
     resources_id=<canteen id>&date=YYYY-MM-DD
Only the Python standard library is used.
"""
import datetime as dt
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINT = "https://www.stw.berlin/xhr/speiseplan-wochentag.html"
PAGE = "https://www.stw.berlin/mensen/einrichtungen/freie-universit%C3%A4t-berlin/"

CANTEENS = [
    {"id": 322, "slug": "mensa-fu-ii", "name": "Mensa FU II",
     "where": "Otto-von-Simson-Str. 26 · Silberlaube", "campus": "Dahlem"},
    {"id": 323, "slug": "shokudo", "name": "Mensa FU I · Shokudō",
     "where": "Van't-Hoff-Str. 6", "campus": "Dahlem"},
    {"id": 542, "slug": "mensa-fu-pharmazie", "name": "Mensa FU Pharmazie",
     "where": "Königin-Luise-Str. 2–4", "campus": "Dahlem"},
    {"id": 660, "slug": "mensa-fu-koserstra%C3%9Fe", "name": "Mensa FU Koserstraße",
     "where": "Koserstr. 20", "campus": "Dahlem"},
    {"id": 271, "slug": "mensa-fu-herrenhaus-d%C3%BCppel", "name": "Mensa FU Herrenhaus Düppel",
     "where": "Oertzenweg 19b", "campus": "Düppel"},
    {"id": 528, "slug": "mensa-fu-lankwitz-malteserstra%C3%9Fe", "name": "Mensa FU Lankwitz",
     "where": "Malteserstr. 74–100", "campus": "Lankwitz"},
]

UA = "fu-mensa-guide/1.0 (personal menu planner; contact via GitHub repo)"


def post(cid, date):
    data = urllib.parse.urlencode({"resources_id": cid, "date": date}).encode()
    req = urllib.request.Request(ENDPOINT, data=data, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # network hiccup: retry
            err = e
            time.sleep(2 + attempt * 3)
    raise err


def text(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


def price(s):
    m = re.search(r"&euro;\s*([\d,]+)(?:/([\d,]+))?(?:/([\d,]+))?", s)
    if not m:
        return None
    vals = [float(v.replace(",", ".")) if v else None for v in m.groups()]
    return {"student": vals[0], "staff": vals[1], "guest": vals[2]}


def parse_day(raw):
    meals = []
    # split into groups
    parts = re.split(r'<div class="col-md-12 splGroup">', raw)[1:]
    for part in parts:
        group = text(part.split("</div>", 1)[0])
        for block in re.split(r'<div class="row splMeal"', part)[1:]:
            name_m = re.search(r'class="bold">(.*?)</span>', block, re.S)
            if not name_m:
                continue
            kennz = re.search(r'data-kennz="([^"]*)"', block)
            icons = re.findall(r"icons/([^'\"?]+)", block)
            co2 = re.search(r"([\d.,]+)\s*g CO2 / Portion", block)
            h2o = re.search(r"([\d.,]+)\s*l Wasserverbrauch", block)
            flags = []
            if "15.png" in icons:
                flags.append("vegan")
            if "1.png" in icons:
                flags.append("vegetarisch")
            if "41.png" in icons:
                flags.append("fairtrade")
            ampel = next((a.split("_")[1] for a in icons if a.startswith("ampel_")), None)
            co2r = next((a[14:15] for a in icons if a.startswith("CO2_bewertung_") and len(a) > 18), None)
            # allergen labels from tooltip table
            allergens = [text(t) for t in re.findall(r"<td>(.*?)</td>", block)]
            meals.append({
                "group": group,
                "name": text(name_m.group(1)),
                "price": price(block),
                "codes": [c for c in (kennz.group(1).split(",") if kennz else []) if c],
                "allergens": allergens,
                "flags": flags,
                "ampel": ampel,
                "co2_g": float(co2.group(1).replace(",", ".")) if co2 else None,
                "co2_rating": co2r,
                "water_l": float(h2o.group(1).replace(",", ".")) if h2o else None,
            })
    return meals


def main(out):
    today = dt.date.today()
    monday = today - dt.timedelta(days=today.weekday())
    days = [monday + dt.timedelta(days=i) for i in range(12) if (monday + dt.timedelta(days=i)).weekday() < 5]
    result = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": "https://www.stw.berlin (studierendenWERK BERLIN, official)",
        "week_start": monday.isoformat(),
        "canteens": [],
    }
    for c in CANTEENS:
        entry = dict(c, url=PAGE + c["slug"] + ".html", days={})
        for d in days:
            try:
                raw = post(c["id"], d.isoformat())
                entry["days"][d.isoformat()] = parse_day(raw)
            except Exception as e:
                print(f"warn: {c['name']} {d}: {e}", file=sys.stderr)
                entry["days"][d.isoformat()] = None
            time.sleep(0.7)  # be polite to the server
        result["canteens"].append(entry)
        n = sum(len(v or []) for v in entry["days"].values())
        print(f"{c['name']}: {n} items over {len(days)} days")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/data/menus.json")
