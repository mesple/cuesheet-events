"""每日抓取文化部藝文活動開放資料，篩出電影音樂相關活動。

資料來源：文化部藝文活動開放資料（政府資料開放授權條款）
輸出：events.json（篩選後的活動）、last_run.json（執行紀錄）
"""
import json
import re
import sys
import urllib.request
from datetime import date, datetime, timezone, timedelta

API = "https://cloud.culture.tw/frontsite/trans/SearchShowAction.do?method=doFindTypeJ&category={}"
CATEGORIES = {"1": "音樂", "7": "講座", "8": "電影", "17": "演唱會"}
TW = timezone(timedelta(hours=8))
CITIES = ["臺北市", "新北市", "桃園市", "臺中市", "臺南市", "高雄市", "基隆市", "新竹市",
          "嘉義市", "新竹縣", "苗栗縣", "彰化縣", "南投縣", "雲林縣", "嘉義縣", "屏東縣",
          "宜蘭縣", "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣"]


def load_keywords(path="keywords.txt"):
    groups, current = {}, None
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^\[(.+)\]$", line)
        if m:
            current = m.group(1)
            groups[current] = []
        elif current:
            groups[current].append(line.lower())
    return (groups.get("強關鍵字", []), groups.get("電影類", []), groups.get("音樂類", []),
            groups.get("候補", []))


def matches(text, strong, film, music):
    t = text.lower()
    hit = [k for k in strong if k in t]
    if hit:
        return hit
    f = [k for k in film if k in t]
    m = [k for k in music if k in t]
    return f + m if f and m else []


def city_of(address):
    a = (address or "").replace("台", "臺").strip()
    for c in CITIES:
        if a.startswith(c) or c in a[:8]:
            return c
    return "其他／未標示"


def parse_date(s):
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except (ValueError, AttributeError):
            pass
    return None


def fetch(cat):
    req = urllib.request.Request(API.format(cat), headers={"User-Agent": "cuesheet-events (GitHub Actions)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8-sig"))


def main():
    strong, film, music, maybe = load_keywords()
    candidates = []
    today = datetime.now(TW).date()
    log = {"run_at": datetime.now(TW).isoformat(timespec="seconds"), "categories": {}}
    events, seen = [], set()
    index = []  # 所有抓到的活動（未篩選），供檢查漏抓

    for cat, name in CATEGORIES.items():
        try:
            data = fetch(cat)
            log["categories"][name] = {"fetched": len(data), "error": None}
        except Exception as e:  # 記錄失敗原因，不中斷其他類別
            log["categories"][name] = {"fetched": 0, "error": f"{type(e).__name__}: {e}"}
            continue

        for ev in data:
            index.append({
                "uid": ev.get("UID"),
                "category": name,
                "title": ev.get("title") or ev.get("titile") or "",
                "performer": ev.get("showUnit") or "",
                "description": ev.get("descriptionFilterHtml") or "",
                "web": ev.get("sourceWebPromote") or "",
                "start_date": ev.get("startDate"),
            })
            uid = ev.get("UID")
            if uid in seen:
                continue
            title = ev.get("title") or ev.get("titile") or ""
            text = " ".join([title, ev.get("descriptionFilterHtml") or "", ev.get("showUnit") or ""])
            hit = matches(text, strong, film, music)
            if not hit:
                weak = [k for k in maybe if k in text.lower()]
                end = parse_date(ev.get("endDate") or "")
                if weak and not (end and end.date() < today):
                    candidates.append({"title": title, "category": name,
                                       "start_date": ev.get("startDate"),
                                       "web": ev.get("sourceWebPromote"),
                                       "matched_keywords": weak})
                continue
            end = parse_date(ev.get("endDate") or "")
            if end and end.date() < today:
                continue
            shows = []
            for s in ev.get("showInfo") or []:
                shows.append({
                    "time": s.get("time"),
                    "end_time": s.get("endTime"),
                    "venue": s.get("locationName"),
                    "address": s.get("location"),
                    "city": city_of(s.get("location")),
                    "lat": s.get("latitude"),
                    "lng": s.get("longitude"),
                    "on_sale": s.get("onSales"),
                    "price": s.get("price"),
                })
            seen.add(uid)
            events.append({
                "uid": uid,
                "title": title,
                "category": name,
                "start_date": ev.get("startDate"),
                "end_date": ev.get("endDate"),
                "organizer": ev.get("masterUnit"),
                "performer": ev.get("showUnit"),
                "description": (ev.get("descriptionFilterHtml") or "")[:500],
                "image": ev.get("imageUrl") or ev.get("imageURL"),
                "web": ev.get("sourceWebPromote"),
                "tickets": ev.get("webSales"),
                "source_site": ev.get("sourceWebName"),
                "cities": sorted({s["city"] for s in shows}),
                "shows": shows,
                "matched_keywords": hit,
            })

    events.sort(key=lambda e: e.get("start_date") or "")
    log["matched_events"] = len(events)
    log["candidates"] = len(candidates)
    ok = any(v["error"] is None for v in log["categories"].values())

    if ok:  # 全部類別都失敗時，保留上一次的 events.json，不用空檔覆蓋
        with open("events.json", "w", encoding="utf-8") as f:
            json.dump({"updated": log["run_at"],
                       "source": "文化部藝文活動開放資料（政府資料開放授權條款）",
                       "events": events}, f, ensure_ascii=False, indent=1)
        with open("candidates.json", "w", encoding="utf-8") as f:
            json.dump(candidates, f, ensure_ascii=False, indent=1)
        with open("all_events_index.json", "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=0)
    with open("last_run.json", "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=1)

    print(json.dumps(log, ensure_ascii=False, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
