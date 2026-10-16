# cuesheet-events

Cue Sheet 電子報的臺灣電影音樂活動資料。

- 每天由 GitHub Actions 抓取文化部藝文活動開放資料（音樂、講座、電影、演唱會四類），篩出電影音樂相關活動。
- `events.json`：篩選結果，含場次、場地、縣市、售票連結。
- `last_run.json`：最近一次執行紀錄（各類別抓到幾筆、有無錯誤）。
- `keywords.txt`：篩選關鍵字，可直接在 GitHub 網頁上編輯，隔天生效。

資料來源：文化部藝文活動開放資料，依政府資料開放授權條款使用。
- `build_section.py`：把 events.json 排成 Cue Sheet 最後一欄「近期國內電影音樂活動」的 HTML。
  例：`python build_section.py events.json 2026-11-16 60 preview.html`，另會輸出 `preview_section.html`（可直接貼進電子報）。

## 新聞補漏：manual_events.json（2026-10-17 新增）

民間主辦單位（如 MNA 牛耳藝術）常不登錄文化部開放資料，每期用新聞搜尋補進 `manual_events.json`，格式同 `events.json`，另加：

- `source`：一律為「新聞」
- `source_links`：主辦頁、售票頁或新聞連結
- `note`：（選填）例如「依新聞，未經官方頁確認」
- 場次 `time_tbd: true`：開演時間未公布時使用，`time` 只寫日期

`build_section.py` 會自動讀取同一資料夾的 `manual_events.json` 併入；同一天、同場館已在開放資料中的場次不重複列，已過期的場次自動略過。

## 抓取防護（2026-10-17 新增）

API 偶爾只回傳部分資料（2026-10-16 音樂類從 489 筆掉到 19 筆）。某類別筆數低於基準的 50% 時，該類別視為不完整，沿用上一次的活動，`last_run.json` 會記錄原因與 `carried_over`。
