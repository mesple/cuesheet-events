"""產生 Cue Sheet「近期國內電影音樂活動」欄目的 HTML 片段與預覽頁。

用法：python build_section.py events.json 發刊日(YYYY-MM-DD) 天數 輸出檔 [線上活動頁網址]
"""
import json
import os
import sys
from datetime import datetime, timedelta
from html import escape

REGIONS = [
    ("北部", ["臺北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣", "宜蘭縣"]),
    ("中部", ["苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣"]),
    ("南部", ["嘉義市", "嘉義縣", "臺南市", "高雄市", "屏東縣"]),
    ("東部與離島", ["花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣"]),
]
WEEK = "一二三四五六日"
SANS = ("-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC','Noto Sans TC',"
        "'Microsoft JhengHei','微軟正黑體',Arial,sans-serif")
SERIF = ("Georgia,'Times New Roman','PingFang TC','Noto Sans TC','Microsoft JhengHei',"
         "'微軟正黑體',sans-serif")


def region_of(city):
    for name, cities in REGIONS:
        if city in cities:
            return name
    return None


def parse(s):
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d"):
        try:
            return datetime.strptime((s or "").strip(), fmt)
        except ValueError:
            pass
    return None


def kind(ev):
    t = ev["title"] + ev.get("category", "")
    if "講座" in t or "大師課" in t or ev.get("category") == "講座":
        return "講座"
    if "影展" in t or ev.get("category") == "電影":
        return "影展活動"
    return "音樂會"


def short_venue(v):
    return (v or "").replace("臺北市", "").replace("（", "（").strip() or "場地未標示"


def norm_venue(v):
    return (v or "").replace("臺", "台").replace(" ", "").replace("國家音樂廳", "音樂廳")


def merge_manual(events, manual):
    """把新聞補漏的活動併入：同一天、同場館已在開放資料中的場次不重複列。"""
    have = {(parse(s["time"]).date(), norm_venue(s["venue"]))
            for ev in events for s in ev["shows"] if parse(s["time"])}
    merged = list(events)
    for ev in manual:
        shows = [s for s in ev["shows"]
                 if (parse(s["time"]).date(), norm_venue(s["venue"])) not in have]
        if shows:
            merged.append(dict(ev, shows=shows))
    return merged


def build(events, issue_date, days):
    start = issue_date
    end = issue_date + timedelta(days=days)
    rows = {name: [] for name, _ in REGIONS}
    dropped = []
    for ev in events:
        by_region = {}
        for s in ev["shows"]:
            t = parse(s["time"])
            reg = region_of(s["city"])
            if not t or not reg or not (start <= t < end):
                continue
            by_region.setdefault(reg, []).append((t, s))
        if not by_region:
            dropped.append(ev["title"])
            continue
        # 一列＝同一節目、同一天、同一場館；同天多場合併成一列並列出各場時間，
        # 不同場館或不同日期分開列（編輯 2026-10-18 指定）
        for reg, shows in by_region.items():
            groups = {}
            for t, s in shows:
                groups.setdefault((t.date(), norm_venue(s["venue"])), []).append((t, s))
            for g in groups.values():
                g.sort(key=lambda x: x[0])
                rows[reg].append((g[0][0], ev, g))
    for reg in rows:
        rows[reg].sort(key=lambda r: r[0])
    return rows, dropped


def item_html(first, ev, shows):
    dates = sorted({t.date() for t, _ in shows})
    if len(dates) == 1:
        d = dates[0]
        date_txt = f"{d.month}/{d.day}"
        if any(s.get("time_tbd") for _, s in shows):
            times = "時間未公布"
        else:
            times = "、".join(sorted({f"{t:%H:%M}" for t, _ in shows}))
        sub = f"（{WEEK[d.weekday()]}）{times}"
    else:
        if len(dates) <= 3:
            date_txt = "<br>".join(f"{d.month}/{d.day}" for d in dates)
        else:
            date_txt = f"{dates[0].month}/{dates[0].day}–{dates[-1].month}/{dates[-1].day}"
        sub = f"共 {len(dates)} 場"
    venues = []
    for _, s in shows:
        v = f"{s['city'][:2]}・{s['venue'] or '場地未標示'}"
        if v not in venues:
            venues.append(v)
    link = ev.get("tickets") or ev.get("web")
    link_html = (f' · <a href="{escape(link)}" style="color:#01696F;">購票／詳情</a>'
                 if link else "")
    org = ev.get("organizer") or ""
    if isinstance(org, list):
        org = "、".join(o for o in org if o)
    if org:
        org_html = f" · 主辦：{escape(org)}"
    elif ev.get("performer"):
        org_html = f" · 演出：{escape(ev['performer'])}"
    else:
        org_html = ""
    if ev.get("note"):  # note 會顯示給讀者；內部註記請寫在 internal_note
        org_html += f" · {escape(ev['note'])}"
    return f"""<tr>
<td width="86" valign="top" style="padding:10px 12px 10px 0;border-top:1px dotted #D4D1CA;font-family:{SANS};">
<div style="font-size:17px;font-weight:700;line-height:1.2;color:#28251D;">{date_txt}</div>
<div style="font-size:11px;line-height:1.5;color:#7A7974;">{sub}</div></td>
<td valign="top" style="padding:10px 0;border-top:1px dotted #D4D1CA;">
<div style="font-size:15px;font-weight:700;line-height:1.45;color:#28251D;">{escape(ev['title'])}</div>
<div style="font-family:{SANS};font-size:12px;line-height:1.6;color:#55534C;margin-top:2px;"><span style="display:inline-block;border:1px solid #01696F;color:#01696F;padding:0 5px;margin-right:6px;font-size:11px;line-height:1.5;">{kind(ev)}</span>{escape('、'.join(venues))}{org_html}{link_html}</div>
</td></tr>"""


def section_html(rows, issue_date, days, page_url):
    end = issue_date + timedelta(days=days - 1)
    parts = [f"""<!-- 11 TAIWAN EVENTS -->
<tr><td class="pad" style="padding:24px 28px 4px 28px;">
  <div style="margin:0 0 14px;padding-top:8px;border-top:1px solid #28251D;font-family:{SANS};font-size:13px;font-weight:700;letter-spacing:.08em;line-height:1.4;color:#28251D;">近期國內電影音樂活動 <span style="display:inline-block;font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#7A7974;margin-left:8px;">Upcoming in Taiwan</span></div>
</td></tr>
<tr><td class="pad" style="padding:0 28px 4px 28px;">
<div style="font-size:14px;line-height:1.7;color:#55534C;margin-bottom:6px;">{issue_date.month}/{issue_date.day}–{end.month}/{end.day} 全台電影、動畫與遊戲音樂的音樂會與講座，依地區、日期排列。</div>"""]
    if page_url and page_url != "#":  # 線上活動頁建好才顯示；放在開頭說明下方，讓讀者先選地區（編輯 2026-10-18 指定）
        from urllib.parse import quote
        btn = ("display:inline-block;margin:6px 6px 0 0;padding:4px 12px;border:1px solid #01696F;"
               "border-radius:999px;color:#01696F;font-weight:700;text-decoration:none;font-size:13px;line-height:1.6;background:#FFFFFF;")
        links = "".join(f'<a href="{page_url}?region={quote(name)}" style="{btn}">{name}</a>'
                        for name, _ in REGIONS)
        parts.append(f"""<div style="margin:10px 0 4px;padding:12px 14px;background:#EEF4F3;border-left:3px solid #01696F;font-size:14px;line-height:1.7;">
<div>先選你的地區，看完整場次、加入行事曆：</div>
<div>{links}<a href="{page_url}" style="{btn}">全部</a></div></div>""")
    for name, _ in REGIONS:
        items = rows[name]
        if not items:
            continue
        parts.append(f"""<div style="font-family:{SERIF};font-size:19px;font-weight:700;line-height:1.35;margin:18px 0 4px;color:#28251D;">{name}</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-collapse:collapse;">""")
        parts += [item_html(*it) for it in items]
        parts.append("</table>")
    parts.append(f"""<div style="font-family:{SANS};font-size:11px;line-height:1.6;color:#7A7974;margin-top:12px;">活動資料來源：文化部藝文活動開放資料、各主辦單位公告與新聞報導；場次以主辦單位公告為準。</div>
</td></tr>""")
    return "\n".join(parts)


def preview_page(section):
    return f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cue Sheet｜近期國內電影音樂活動欄（試排）</title>
<style>@media (max-width:540px){{.pad{{padding-left:16px!important;padding-right:16px!important}}}}</style></head>
<body style="margin:0;padding:0;background:#F2F0EA;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#F2F0EA;"><tr><td align="center" style="padding:20px 10px;">
<table role="presentation" width="760" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:760px;background:#FBFAF6;border:1px solid #D4D1CA;font-family:{SANS};color:#28251D;">
<tr><td class="pad" style="padding:28px 28px 18px 28px;border-bottom:5px solid #28251D;">
<div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#7A7974;">Monthly film music newsletter · 欄目試排</div>
<div style="margin:8px 0 0;font-family:{SERIF};font-size:56px;line-height:.95;font-weight:700;letter-spacing:-.04em;color:#28251D;">Cue Sheet</div></td></tr>
<tr><td class="pad" style="padding:18px 28px 0 28px;font-size:13px;line-height:1.7;color:#7A7974;">…… 第 10 欄「週末cue一下」結束 ……</td></tr>
{section}
<tr><td class="pad" style="padding:18px 28px 28px 28px;font-size:13px;line-height:1.7;color:#7A7974;">…… 接頁尾（本期使用來源、資料蒐集截止日）……</td></tr>
</table></td></tr></table></body></html>"""


if __name__ == "__main__":
    src, issue, days, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    data = json.load(open(src, encoding="utf-8"))
    issue_date = datetime.strptime(issue, "%Y-%m-%d")
    events = data["events"]
    manual_path = os.path.join(os.path.dirname(os.path.abspath(src)), "manual_events.json")
    if os.path.exists(manual_path):  # 新聞搜尋補漏的活動（民間主辦、未登錄開放資料）
        manual = json.load(open(manual_path, encoding="utf-8")).get("events", [])
        events = merge_manual(events, manual)
        print("manual events:", len(manual))
    rows, dropped = build(events, issue_date, days)
    sec = section_html(rows, issue_date, days, sys.argv[5] if len(sys.argv) > 5 else "#")
    open(out, "w", encoding="utf-8").write(preview_page(sec))
    open(out.replace(".html", "_section.html"), "w", encoding="utf-8").write(sec)
    print("kept:", {k: len(v) for k, v in rows.items()})
    print("outside window:", dropped)
    print("section bytes:", len(sec.encode()))
