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

## 線上活動頁（index.html，2026-10-17 新增）

網址：https://mesple.github.io/cuesheet-events/（需在 repo 的 Settings → Pages 開啟：Source 選 Deploy from a branch，Branch 選 main、/ (root)）

- 直接讀取同一 repo 的 `events.json` 與 `manual_events.json`，每天 Actions 更新資料後頁面自動跟著更新，不需另外部署。
- 可依地區、城市、類型篩選；每場可加入 Google 日曆或下載 .ics（Apple 行事曆、Outlook）。
- 篩選條件會寫進網址，電子報可直接連到特定地區，例如 `?region=南部`、`?city=臺中市`。
- 產生電子報欄目時把網址當第 5 個參數傳給 `build_section.py`，欄尾就會出現「線上活動頁」連結框。

## 防止排程停用（2026-10-22 新增）

GitHub 會停用公開 repo 中 60 天沒有活動的排程。`.github/workflows/keepalive.yml` 每月 1 日檢查，最近 40 天沒有任何提交時，更新 `keepalive.txt` 留下一筆提交。平常每日抓取都有提交，這個流程不會動作。

## 新聞補漏候選（2026-10-22 新增）

每月 1 日、15 日由 Claude 排程任務搜尋新聞，只把候選場次列給編輯審核，**不會自動寫入** `manual_events.json`。編輯確認後才補登。
