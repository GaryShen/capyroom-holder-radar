# 持有者結構雷達 · Holder Structure Radar

免費、開源、繁中的**比特幣持有者結構雷達**。自己從 BigQuery 公開資料集
**增量算出** LTH/STH 供給與成本線,把「現在誰在抱、誰在賣、買的人套牢沒」
合成一句白話判讀,並在訊號觸發時推播(LINE / Telegram)。

> 只做資料呈現與方法拆解,**非投資建議**。每個畫面結尾固定附免責。

---

## 架構(三層 + 一個接點)

```
┌─────────────────────────────────────────────────────────┐
│  資料層  src/holder_radar/bigquery_cohort.py             │  ← BigQuery 公開資料集
│          BigQuery 增量算 cohort 供給 + 已實現市值(成本線) │     (增量,守 1TB/月免費)
│          src/holder_radar/prices.py  CoinGecko 價格       │
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

**`src/` ↔ `app/` 唯一接點**:資料層算完後輸出一份 cohort 時序 `data.json`,
`app/assets/radar.js` 的 `build()` 讀它畫圖。目前 `build()` 用 demo 數字寫死;
BigQuery 完成後換成讀 `data.json` 即接上真實資料。**這是兩層之間唯一的耦合。**

---

## 目錄

```
src/holder_radar/        # Python:資料管線 + 判讀 + 通知(後端)
  config.py              #   常數(155天、免費掃描上限)
  bigquery_cohort.py     #   ⏳ BigQuery 增量算供給+成本線(待 GCP)
  prices.py              #   CoinGecko 價格
  store.py               #   SQLite 快取讀寫
  judge.py               #   ★ 判讀層:訊號 + 繁中合成(純函式)
  notify.py              #   LINE / Telegram 可插拔 adapter
  cli.py                 #   每日入口:算→寫→偵測→(alert才)推
  line_bot.py            #   LINE 查詢(免費 reply)
app/                     # 靜態儀表板(前端,Claude Design 成品,零依賴)
  index.html  assets/styles.css  assets/radar.js
tests/                   # pytest(13 綠;judge/store/prices/notify/cli/line_bot)
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
- `data.json` 接點完成後,每日 workflow 會 commit `data.json` 進 `app/`,Pages 自動換成真實數字。
- **為什麼這樣分**:LINE push 按人頭計費,大眾免費推播做不到 → 儀表板公開一份大家看,**要警報的人 fork 自架、用自己的免費額度**。

## 現況

| 模組 | 狀態 |
|---|---|
| judge / store / prices / notify / cli / line_bot | ✅ 完成,13 tests 綠 |
| app/ 儀表板(三畫面,demo 資料) | ✅ 完成,渲染驗證 |
| bigquery_cohort(供給+成本線) | ⏳ 待 GCP 專案(Task 2/3) |
| data.json 接點 + 真實資料 | ⏳ 待 bigquery_cohort |
| GitHub Actions + LINE OA 自架 | ⏳ 待 secrets(Task 11) |

設計與實作計畫:`影片管理/卡皮鏈上室/持有者結構雷達_LTH-STH/`(設計文件.md / 實作計畫.md)。

---

本內容僅為資料整理,非投資建議。
