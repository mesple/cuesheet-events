# cuesheet-events

Cue Sheet 電子報的臺灣電影音樂活動資料。

- 每天由 GitHub Actions 抓取文化部藝文活動開放資料（音樂、講座、電影、演唱會四類），篩出電影音樂相關活動。
- `events.json`：篩選結果，含場次、場地、縣市、售票連結。
- `last_run.json`：最近一次執行紀錄（各類別抓到幾筆、有無錯誤）。
- `keywords.txt`：篩選關鍵字，可直接在 GitHub 網頁上編輯，隔天生效。

資料來源：文化部藝文活動開放資料，依政府資料開放授權條款使用。
- `build_section.py`：把 events.json 排成 Cue Sheet 最後一欄「近期國內電影音樂活動」的 HTML。
  例：`python build_section.py events.json 2026-11-16 60 preview.html`，另會輸出 `preview_section.html`（可直接貼進電子報）。
