# 持有者結構雷達 — Holder Structure Radar (web)

Standalone implementation of the Claude Design prototype
`project/持有者結構雷達.dc.html`. No build step, no framework — open
`index.html` in any browser.

```
app/
  index.html         # markup for all three surfaces
  assets/
    styles.css       # full styling (editorial / terminal / push)
    radar.js         # build() chart math + DOM rendering + interactions
```

## What it is

A BTC holder-structure dashboard that splits supply into **STH (短期持有者,
< 155 天)** and **LTH (長期持有者,≥ 155 天)**, draws price vs the STH cost
line, and synthesises a plain-Chinese reading. Strictly descriptive — every
view ends with the fixed disclaimer「本內容僅為資料整理,非投資建議」.

## Surfaces (mapped from the design's three frames)

- **Editorial (default)** — Frame A, the light/compact consumer dashboard
  the user landed on: hero judgment + LTH donut + stat grid, STH/LTH
  glossary, price-vs-cost chart beside the signal stack, the
  「歷史怎麼讀」 2017→2026 log-scale history section, and the supply band.
  It is fully responsive and collapses to Frame C's single-column mobile
  layout on narrow screens.
- **Terminal** — Frame B, the dark high-density view. Toggle via the
  **編輯 / 終端機** switch in the top bar.
- **Push showcase** — Frame C's phone dashboard plus the LINE (green) and
  Telegram (blue) notification mockups. Both are plain **text** messages —
  the same synthesised sentence; only the app chrome differs.

The **雷達掃描動畫** checkbox toggles the radar-sweep animation (the
prototype's tweak-panel control).

## Chart math

`radar.js` ports the prototype's `DCLogic.build()` verbatim. All SVG path
geometry — price/cost curves, the underwater (套牢) fill, the cross marker,
the supply band, the donut dash-arrays, and the history bands/episodes — is
computed exactly as in the design so the output matches pixel-for-pixel.

The numbers are the design's reference values (現價 $59,800、STH 成本線
$71,400、套牢 16.2%、LTH 79%、FNG 17); the curves are a simulated demo
series. To wire real data, replace the control-point arrays inside `build()`
(or feed it the cohort time series from the `holder-radar` pipeline described
in `project/uploads/實作計畫.md`).

## Notes

- Fonts (Noto Serif TC / Noto Sans TC / IBM Plex Mono) load from Google
  Fonts; the page degrades gracefully to system fonts offline.
- No external JS/image assets — all visuals are CSS/SVG drawn in code,
  per the project's red-line (素材全程式繪製).
