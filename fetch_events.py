"""每日抓取文化部藝文活動開放資料，篩出電影音樂相關活動。

資料來源：文化部藝文活動開放資料（政府資料開放授權條款）
輸出：events.json（篩選後的活動）、last_run.json（執行紀錄）
"""
import json
import re
import sys
import time
import urllib.request
from datetime import date, datetime, timezone, timedelta

API = "https://cloud.culture.tw/frontsite/trans/SearchShowAction.do?method=doFindTypeJ&category={}"
CATEGORIES = {"1": "音樂", "7": "講座", "8": "電影", "17": "演唱會"}
# 某類別筆數低於基準的這個比例，就視為 API 回傳不完整（2026-10-16 曾發生：音樂類 489 筆掉到 19 筆）
SHRINK_LIMIT = 0.5


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default
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


RETRY_WAITS = [30, 90, 180]  # 失敗或資料不完整時，分別等這麼多秒再重試


def fetch_once(cat):
    req = urllib.request.Request(API.format(cat), headers={"User-Agent": "cuesheet-events (GitHub Actions)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8-sig"))


def fetch(cat, baseline):
    """抓取一個類別；逾時、連線錯誤或筆數驟降時重試。

    回傳 (資料, 嘗試次數, 最後的問題說明或 None)。全部失敗時資料為 None。
    """
    last_problem, best = None, None
    for attempt in range(len(RETRY_WAITS) + 1):
        if attempt:
            time.sleep(RETRY_WAITS[attempt - 1])
        try:
            data = fetch_once(cat)
        except Exception as e:
            last_problem = f"{type(e).__name__}: {e}"
            continue
        if best is None or len(data) > len(best):
            best = data
        if baseline >= 20 and len(data) < baseline * SHRINK_LIMIT:
            last_problem = f"疑似資料不完整：{len(data)} 筆，基準 {baseline} 筆"
            continue
        return data, attempt + 1, None
    return best, len(RETRY_WAITS) + 1, last_problem


def main():
    strong, film, music, maybe = load_keywords()
    candidates = []
    today = datetime.now(TW).date()
    log = {"run_at": datetime.now(TW).isoformat(timespec="seconds"), "categories": {}}
    events, seen = [], set()
    index = []  # 所有抓到的活動（未篩選），供檢查漏抓

    # 上一次的結果：用來偵測「API 只回傳一小部分資料」的情況
    prev_log = load_json("last_run.json", {}).get("categories", {})
    prev_events = load_json("events.json", {}).get("events", [])
    prev_index = load_json("all_events_index.json", [])
    carried = []  # 沿用上一次資料的類別

    for cat, name in CATEGORIES.items():
        prev = prev_log.get(name, {})
        baseline = prev.get("baseline") or prev.get("fetched") or 0
        data, attempts, problem = fetch(cat, baseline)
        if problem:
            # 重試後仍失敗或資料不完整：這個類別沿用上一次的結果，不中斷其他類別
            log["categories"][name] = {
                "fetched": len(data or []), "baseline": baseline, "attempts": attempts,
                "error": f"{problem}（共試 {attempts} 次），沿用上次資料"}
            carried.append(name)
            continue
        log["categories"][name] = {"fetched": len(data), "baseline": len(data),
                                   "attempts": attempts, "error": None}

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

    # 沿用類別：帶回上一次的活動（已結束的仍然排除）與索引
    for name in carried:
        for ev in prev_events:
            end = parse_date(ev.get("end_date") or "")
            if ev.get("category") == name and ev.get("uid") not in seen \
                    and not (end and end.date() < today):
                seen.add(ev.get("uid"))
                events.append(ev)
        index += [e for e in prev_index if e.get("category") == name]
    log["carried_over"] = carried

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
