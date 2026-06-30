# 持有者結構雷達 · Holder Structure Radar

免費、開源、繁中的**比特幣持有者結構雷達**。每日從**免費**的 bgeometrics(無 key)
抓 LTH/STH 供給與成本線,把「現在誰在抱、誰在賣、買的人套牢沒」
合成一句白話判讀,並在訊號觸發時推播(LINE / Telegram)。
(BigQuery 自算為**選配備援**,預設不跑、不花錢。)

> 只做資料呈現與方法拆解,**非投資建議**。每個畫面結尾固定附免責。

---

## 架構(三層 + 一個接點)

```
┌─────────────────────────────────────────────────────────┐
│  資料層  src/holder_radar/bgeometrics.py  ★免費★          │  ← api.bgeometrics.com
│          抓 LTH/STH 供給 + 成本線(免費、無 key、每日)     │     (10次/小時,每日只用4次)
│          src/holder_radar/prices.py  CoinGecko 價格       │
│          src/holder_radar/bigquery_cohort.py  (備援,會花錢)│     (選配,自算驗證用)
│                          │                                │
│                          ▼                                │
│  儲存    src/holder_radar/store.py   SQLite 快取時序       │  data/snapshot.sqlite
│                          │           (clone 即有種子快照)  │
│                          ▼                                │
│  判讀層  src/holder_radar/judge.py   純函式               │  ← 工具的「腦」、差異化
│          訊號偵測(跌穿成本線/供給極值)+ 繁中合成判讀     │     全 TDD、無 I/O
│                          │                                │
│         ┌────────────────┼────────────────┐              │
│         ▼                ▼                ▼              │
│  出口① 儀表板        出口② LINE/TG      出口③ 每日管線    │
│  app/(靜態)        notify.py          cli.py           │
│  ↑ 經 data.json 接點  可插拔 adapter    GitHub Actions    │
└─────────────────────────────────────────────────────────┘
```

**`src/` ↔ `app/` 唯一接點**:資料層每日輸出 `app/assets/data.js`(`window.RADAR_DATA`),
`app/assets/radar.js` 的 `build()` 讀它畫圖。**這是兩層之間唯一的耦合。**

> **cohort 來源**:預設走**免費**的 bgeometrics(無 key、每日自動更新、你帳號零費用)。
> `bigquery_cohort.py` 是**選配備援**(自算驗證用,會計費,預設不跑)。

---

## 目錄

```
src/holder_radar/        # Python:資料管線 + 判讀 + 通知(後端)
  config.py              #   常數(155天)
  bgeometrics.py         #   ★ 免費 cohort 來源(api.bgeometrics.com,無 key)
  bigquery_cohort.py     #   選配備援:BigQuery 自算(會花錢,預設不用)
  prices.py              #   CoinGecko 價格
  store.py               #   SQLite 快取讀寫
  judge.py               #   ★ 判讀層:訊號 + 繁中合成(純函式)
  export.py              #   ★ src↔app 接點:輸出 app/assets/data.js(window.RADAR_DATA)
  notify.py              #   LINE / Telegram 可插拔 adapter
  cli.py                 #   每日入口:算→寫→偵測→(alert才)推
  line_bot.py            #   LINE 查詢(免費 reply)
app/                     # 靜態儀表板(前端,Claude Design 成品,零依賴)
  index.html  assets/styles.css  assets/radar.js  assets/data.js
tests/                   # pytest(22 綠;core/pipeline/bgeometrics/bigquery_cohort)
data/                    # snapshot.sqlite(種子快照,git 追蹤)
.claude/launch.json      # 預覽:preview_start radar-static
```

---

## 為什麼不用前端框架(Vue/React)

儀表板是**唯讀資料視覺化 + 兩個 toggle**,沒有複雜狀態/路由/大量元件。
零依賴、零 build、雙擊就開,自架者 GitHub Pages/Action 丟靜態檔即可。
加框架 = build step + node_modules + 部署變複雜,直接打臉「免費極簡自架」核心。
真要互動再長,中間地帶是 petite-vue / Alpine(無 build);現在用不到。

---

## 開發

```bash
uv run pytest -q              # 跑測試(目前 13 綠)
# 預覽儀表板:preview_start radar-static(見 .claude/launch.json)
```

---

## 部署(公開儀表板 + 自架警報)

| 元件 | 上線在哪 | 伺服器 |
|---|---|---|
| **儀表板 app/** | **你的 GitHub Pages**(一個公開網址,大家直接看)| 無(靜態)|
| **每日算+推播** | **GitHub Actions** 排程(自架者各自 fork、設自己的 LINE OA secrets)| 無(cron)|
| **LINE 互動查詢** | ⏸️ 暫不做(要常駐端點,push-only MVP 先零伺服器)| — |

- 儀表板已可上線:`.github/workflows/pages.yml` 會把 `app/` 發到 Pages。
  你只要 ① 把 repo 推上 GitHub ② Settings → Pages 選 GitHub Actions,公開網址即生效(先 demo 數字)。
- `data.js` 接點完成後,每日 workflow 會 commit `data.js` 進 `app/assets/`,Pages 自動換成真實數字。
- **為什麼這樣分**:LINE push 按人頭計費,大眾免費推播做不到 → 儀表板公開一份大家看,**要警報的人 fork 自架、用自己的免費額度**。

## 現況

| 模組 | 狀態 |
|---|---|
| judge / store / prices / notify / cli / line_bot | ✅ 完成,22 tests 綠 |
| app/ 儀表板 + 真實資料(`data.js`) | ✅ 完成、已上線、渲染驗證 |
| **bgeometrics 免費 cohort 來源** | ✅ 完成:cohort 每日免費更新(無 BigQuery、零費用) |
| GitHub Pages 部署 | ✅ 上線 https://garyshen.github.io/capyroom-holder-radar/ |
| 每日 / 快照 GitHub Actions | ✅ daily(免費)已就緒;snapshot(BigQuery)選配、加防呆 |
| LINE OA 自架推播 | ⏳ 選配:設 `LINE_TOKEN`/`LINE_TO` secrets 即啟用 |
| 成本線歷史曲線 | 🟡 隨每日累積逐步填實(現為單點 forward-fill) |

設計與實作計畫:`影片管理/卡皮鏈上室/持有者結構雷達_LTH-STH/`(設計文件.md / 實作計畫.md)。

---

## 自架(免費)

1. **Fork** 這個 repo。
2. Settings → **Pages** → Source 選 **GitHub Actions** → 你的公開儀表板網址即生效。
   - `Daily update` workflow 每天免費跑(CoinGecko 現價 + 重生 data.js),**不需任何 secret**。
3. (選配)**LINE 警報**:Settings → Secrets 設 `LINE_TOKEN`、`LINE_TO`(自己的 LINE 官方帳號 Messaging API)→ 跌穿成本線時推你自己(免費 200則/月個人盯盤夠用)。
4. (選配,**可能花錢**)**自己更新 cohort**:設 `GCP_SA_JSON`、`GCP_PROJECT` + `HOLDER_RADAR_RUN_SNAPSHOT=1`,手動跑 `Cohort snapshot`(BigQuery,每次掃描約 0.45TB)。

> ⚠️ **「1TB/月免費」只在 Sandbox(未綁帳單)帳號保證有效。** 綁了帳單的帳號可能**拿不到免費額度** → 每次約 **$7 USD**(實測)。
> 不想花錢就**別跑 snapshot**——網站靠每日免費的 CoinGecko 價格照常更新,cohort 用現有快照即可。要更新 cohort 又要真免費,請用 Sandbox 帳號。
> 程式有防呆:未設 `HOLDER_RADAR_RUN_SNAPSHOT=1` 不會跑 BigQuery;每次查詢前先 dry-run 量測(免費)。

---

本內容僅為資料整理,非投資建議。
