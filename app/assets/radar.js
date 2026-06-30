/*
 * 持有者結構雷達 — Holder Structure Radar
 * Standalone port of the Claude Design prototype (持有者結構雷達.dc.html).
 *
 * The original prototype relied on the proprietary Claude Design runtime
 * (support.js) for its <x-dc> template, sc-for / sc-if directives, {{ }}
 * bindings and a DCLogic `build()` method. This file reproduces that
 * computation in plain JS and renders the charts into real DOM, so the
 * dashboard runs in any browser with no framework.
 *
 * `build()` below is a faithful port of the prototype's DCLogic.build():
 * all chart geometry (price vs STH cost line, supply band, donut, and the
 * 2017→2026 history chart) is computed exactly as in the design so the
 * visual output matches pixel-for-pixel. Data is a simulated reference
 * curve — swap the `build()` inputs for real pipeline output when wiring
 * the BigQuery/CoinGecko backend.
 */
(function () {
  "use strict";

  // ----------------------------------------------------------------------
  // build() — verbatim port of the prototype's DCLogic.build()
  // ----------------------------------------------------------------------
  function build() {
    const N = 180;
    const days = [];
    const end = new Date(Date.UTC(2026, 5, 29));
    for (let i = N - 1; i >= 0; i--) {
      const d = new Date(end);
      d.setUTCDate(d.getUTCDate() - i);
      days.push(d);
    }
    const lerp = (a, b, t) => a + (b - a) * t;
    const seg = (ctrl) => {
      const out = [];
      for (let i = 0; i < N; i++) {
        let a = ctrl[0], b = ctrl[ctrl.length - 1];
        for (let k = 0; k < ctrl.length - 1; k++) {
          if (i >= ctrl[k][0] && i <= ctrl[k + 1][0]) { a = ctrl[k]; b = ctrl[k + 1]; break; }
        }
        const t = (i - a[0]) / ((b[0] - a[0]) || 1);
        out.push(lerp(a[1], b[1], t));
      }
      return out;
    };
    let price = seg([[0, 92000], [20, 99500], [50, 87500], [80, 92000], [110, 79500], [135, 73200], [150, 67500], [165, 62500], [179, 59800]]);
    price = price.map((v, i) => v + Math.sin(i * 0.55) * 850 + Math.sin(i * 0.19) * 1300);
    price[N - 1] = 59800;
    let cost = seg([[0, 63500], [42, 68200], [82, 71200], [120, 73300], [179, 71400]]);
    cost = cost.map((v, i) => v + Math.sin(i * 0.12) * 90);
    cost[N - 1] = 71400;
    let lth = seg([[0, 74.2], [60, 75.8], [110, 77.4], [150, 78.4], [179, 79.0]]);
    lth = lth.map((v, i) => v + Math.sin(i * 0.3) * 0.18);
    lth[N - 1] = 79.0;

    // 真實資料注入(window.RADAR_DATA,由 data.js 提供);無則沿用上面的 demo 曲線
    if (window.RADAR_DATA) {
      const D = window.RADAR_DATA;
      if (D.price && D.price.length === N) price = D.price.slice();
      if (D.cost && D.cost.length === N) cost = D.cost.slice();
      if (D.lth && D.lth.length === N) lth = D.lth.slice();
    }

    // chart 1 geometry
    const W = 1000, H = 360, pT = 14, pB = 30, pL = 2, pR = 2, yMin = 55000, yMax = 103000;
    const X = i => pL + i / (N - 1) * (W - pL - pR);
    const Y = v => pT + (1 - (v - yMin) / (yMax - yMin)) * (H - pT - pB);
    const pathOf = arr => "M " + arr.map((v, i) => X(i).toFixed(1) + " " + Y(v).toFixed(1)).join(" L ");
    const pPath = pathOf(price), cPath = pathOf(cost);
    const baseY = (H - pB).toFixed(1);
    const pArea = pPath + " L " + X(N - 1).toFixed(1) + " " + baseY + " L " + X(0).toFixed(1) + " " + baseY + " Z";
    let ci = N - 1;
    for (let i = 1; i < N; i++) { if (price[i - 1] >= cost[i - 1] && price[i] < cost[i]) { ci = i; break; } }
    let uw = "M " + X(ci).toFixed(1) + " " + Y(cost[ci]).toFixed(1);
    for (let i = ci + 1; i < N; i++) uw += " L " + X(i).toFixed(1) + " " + Y(cost[i]).toFixed(1);
    for (let i = N - 1; i >= ci; i--) uw += " L " + X(i).toFixed(1) + " " + Y(price[i]).toFixed(1);
    uw += " Z";
    const crLabel = (days[ci].getUTCMonth() + 1) + "/" + days[ci].getUTCDate();
    const priceTicks = [100000, 90000, 80000, 70000, 60000].map(v => ({ y: Y(v).toFixed(1), label: "$" + (v / 1000) + "k" }));
    const xTicks = [0, 36, 72, 108, 144, 179].map(i => ({ x: X(i).toFixed(1), label: (days[i].getUTCMonth() + 1) + "月" }));

    // chart 2 supply band
    const W2 = 1000, H2 = 220, qT = 10, qB = 22;
    const X2 = i => i / (N - 1) * W2;
    const Y2 = p => qT + (1 - p / 100) * (H2 - qT - qB);
    const lthLine = "M " + lth.map((v, i) => X2(i).toFixed(1) + " " + Y2(v).toFixed(1)).join(" L ");
    const baseY2 = (H2 - qB).toFixed(1);
    const lthArea = lthLine + " L " + W2 + " " + baseY2 + " L 0 " + baseY2 + " Z";
    let sthArea = "M 0 " + qT.toFixed(1) + " L " + W2 + " " + qT.toFixed(1);
    for (let i = N - 1; i >= 0; i--) sthArea += " L " + X2(i).toFixed(1) + " " + Y2(lth[i]).toFixed(1);
    sthArea += " Z";

    // donut large (r=80) —— 比例優先用真實資料
    const donutR = (window.RADAR_DATA && window.RADAR_DATA.donut) ? window.RADAR_DATA.donut.lth_pct : 0.79;
    const C = 2 * Math.PI * 80;
    const lthLen = donutR * C;
    // donut small (r=56)
    const Csm = 2 * Math.PI * 56;
    const lthLenSm = donutR * Csm;

    // ---- long-horizon history (2017-01 .. 2026-06, monthly) ----
    const M = 114;
    const interp = (ctrl, n) => {
      const out = [];
      for (let i = 0; i < n; i++) {
        let a = ctrl[0], b = ctrl[ctrl.length - 1];
        for (let k = 0; k < ctrl.length - 1; k++) {
          if (i >= ctrl[k][0] && i <= ctrl[k + 1][0]) { a = ctrl[k]; b = ctrl[k + 1]; break; }
        }
        const t = (i - a[0]) / ((b[0] - a[0]) || 1);
        out.push(a[1] + (b[1] - a[1]) * t);
      }
      return out;
    };
    let hp = interp([[0, 1000], [11, 19000], [23, 3300], [30, 12000], [38, 5200], [46, 18000], [50, 58000], [58, 68000], [65, 19000], [70, 16500], [83, 42000], [86, 72000], [92, 58000], [101, 88000], [108, 99000], [113, 59800]], M);
    hp = hp.map((v, i) => v * (1 + Math.sin(i * 0.9) * 0.025));
    hp[M - 1] = 59800;
    const hc = hp.map((v, i) => { let s = 0, n = 0; for (let k = Math.max(0, i - 5); k <= i; k++) { s += hp[k]; n++; } return s / n; });
    const HW = 1000, HH = 300, hT = 14, hB = 24, lyMin = Math.log10(700), lyMax = Math.log10(135000);
    const HX = i => (i / (M - 1) * HW);
    const HY = v => hT + (1 - (Math.log10(v) - lyMin) / (lyMax - lyMin)) * (HH - hT - hB);
    const histPrice = "M " + hp.map((v, i) => HX(i).toFixed(1) + " " + HY(v).toFixed(1)).join(" L ");
    const histCost = "M " + hc.map((v, i) => HX(i).toFixed(1) + " " + HY(v).toFixed(1)).join(" L ");
    // underwater bands (full height) where price<cost
    const histBands = []; let st = null;
    for (let i = 0; i < M; i++) {
      const u = hp[i] < hc[i];
      if (u && st === null) st = i;
      if ((!u || i === M - 1) && st !== null) {
        const e = (i === M - 1 && u) ? i : i - 1;
        histBands.push({ x: HX(st).toFixed(1), w: Math.max(2, HX(e) - HX(st)).toFixed(1) });
        st = null;
      }
    }
    const histBaseH = (HH - hB).toFixed(1);
    const histYTicks = [100000, 10000, 1000].map(v => ({ y: HY(v).toFixed(1), yp: (HY(v) / HH * 100).toFixed(1), label: "$" + (v / 1000) + "k" }));
    const histXTicks = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026].map(y => ({ x: HX((y - 2017) * 12).toFixed(1), label: "’" + String(y).slice(2) }));
    const epDefs = [
      { i: 23, label: "2018 熊市", sub: "STH 全面套牢,LTH 默默吸籌築底", c: "#3E6B86" },
      { i: 38, label: "2020 COVID", sub: "流動性崩跌,價格瞬間跌穿", c: "#3E6B86" },
      { i: 70, label: "2022 FTX", sub: "投降延續數月,成本線一路下移", c: "#3E6B86" },
      { i: 92, label: "2024 回測", sub: "短暫跌穿後收復成本線", c: "#3E6B86" },
      { i: 113, label: "2026 現在", sub: "再次跌穿,STH 平均套牢約 16%", c: "#E8512A" }
    ];
    const histEpisodes = epDefs.map((e, k) => ({ x: HX(e.i).toFixed(1), xp: (HX(e.i) / HW * 100).toFixed(2), y: HY(hp[e.i]).toFixed(1), n: k + 1, label: e.label, sub: e.sub, c: e.c }));

    return {
      pPath, cPath, pArea, uw,
      crX: X(ci).toFixed(1), crY: Y(cost[ci]).toFixed(1), crLabel,
      priceTicks, xTicks, lthArea, sthArea, lthLine,
      donutDashLth: lthLen.toFixed(1) + " " + (C - lthLen).toFixed(1),
      donutDashSth: (C - lthLen).toFixed(1) + " " + lthLen.toFixed(1),
      donutOff: (-lthLen).toFixed(1),
      donutDashLthSm: lthLenSm.toFixed(1) + " " + (Csm - lthLenSm).toFixed(1),
      donutDashSthSm: (Csm - lthLenSm).toFixed(1) + " " + lthLenSm.toFixed(1),
      donutOffSm: (-lthLenSm).toFixed(1),
      histPrice, histCost, histBands, histBaseH, histYTicks, histXTicks, histEpisodes
    };
  }

  // ----------------------------------------------------------------------
  // small DOM helpers
  // ----------------------------------------------------------------------
  const SVGNS = "http://www.w3.org/2000/svg";
  const svgEl = (tag, attrs) => {
    const el = document.createElementNS(SVGNS, tag);
    for (const k in attrs) el.setAttribute(k, attrs[k]);
    return el;
  };
  const setSvg = (host, viewBox, children, extra) => {
    const svg = svgEl("svg", Object.assign({ viewBox, preserveAspectRatio: "none" }, extra || {}));
    children.forEach(c => svg.appendChild(c));
    host.innerHTML = "";
    host.appendChild(svg);
    return svg;
  };
  const $ = sel => document.querySelector(sel);

  // ----------------------------------------------------------------------
  // chart renderers
  // ----------------------------------------------------------------------

  // Price vs STH cost line. opts vary per surface (editorial / terminal / mobile).
  function renderPriceChart(host, v, opts) {
    if (!host) return;
    const kids = [];
    if (opts.grid) {
      v.priceTicks.forEach(t => kids.push(svgEl("line", { x1: 0, x2: 1000, y1: t.y, y2: t.y, stroke: opts.grid, "stroke-width": 1 })));
    }
    kids.push(svgEl("path", { d: v.uw, fill: "rgba(232,81,42,.16)" }));
    kids.push(svgEl("path", { d: v.cPath, fill: "none", stroke: "#E8512A", "stroke-width": opts.costSW, "stroke-dasharray": opts.costDash, "vector-effect": "non-scaling-stroke" }));
    kids.push(svgEl("path", { d: v.pPath, fill: "none", stroke: opts.priceStroke, "stroke-width": opts.priceSW, "vector-effect": "non-scaling-stroke" }));
    if (opts.crossLine) {
      kids.push(svgEl("line", { x1: v.crX, x2: v.crX, y1: 0, y2: 360, stroke: "rgba(232,81,42,.5)", "stroke-width": 1, "stroke-dasharray": "3 4" }));
    }
    if (opts.dot) {
      const dotAttrs = { cx: v.crX, cy: v.crY, r: opts.dot, fill: "#E8512A" };
      if (opts.dotStroke) { dotAttrs.stroke = opts.dotStroke; dotAttrs["stroke-width"] = 2; }
      kids.push(svgEl("circle", dotAttrs));
    }
    setSvg(host, "0 0 1000 360", kids, { style: "width:100%;height:" + opts.height + ";display:block;" });
  }

  function renderSupplyBand(host, v, opts) {
    if (!host) return;
    const kids = [
      svgEl("path", { d: v.lthArea, fill: opts.lthFill }),
      svgEl("path", { d: v.sthArea, fill: opts.sthFill }),
      svgEl("path", { d: v.lthLine, fill: "none", stroke: opts.lthStroke, "stroke-width": opts.lthSW, "vector-effect": "non-scaling-stroke" })
    ];
    setSvg(host, "0 0 1000 220", kids, { style: "width:100%;height:" + opts.height + ";display:block;" });
  }

  function renderDonut(host, v, opts) {
    if (!host) return;
    const r = opts.r, sw = opts.sw, vb = opts.viewBox, cx = opts.cx, cy = opts.cy;
    const kids = [
      svgEl("circle", { cx, cy, r, fill: "none", stroke: "rgba(33,28,22,.08)", "stroke-width": sw }),
      svgEl("circle", { cx, cy, r, fill: "none", stroke: "#3E6B86", "stroke-width": sw, "stroke-dasharray": opts.dashLth, "stroke-linecap": "butt" }),
      svgEl("circle", { cx, cy, r, fill: "none", stroke: "#E8512A", "stroke-width": sw, "stroke-dasharray": opts.dashSth, "stroke-dashoffset": opts.off, "stroke-linecap": "butt" })
    ];
    setSvg(host, vb, kids, { style: "position:absolute;inset:0;transform:rotate(-90deg);" });
  }

  function renderHistory(v) {
    const host = $("#hist-chart");
    if (!host) return;
    const kids = [];
    v.histBands.forEach(b => kids.push(svgEl("rect", { x: b.x, y: 0, width: b.w, height: v.histBaseH, fill: "rgba(232,81,42,.11)" })));
    v.histYTicks.forEach(t => kids.push(svgEl("line", { x1: 0, x2: 1000, y1: t.y, y2: t.y, stroke: "rgba(33,28,22,.08)", "stroke-width": 1 })));
    kids.push(svgEl("path", { d: v.histCost, fill: "none", stroke: "#E8512A", "stroke-width": 2, "stroke-dasharray": "6 5", "vector-effect": "non-scaling-stroke" }));
    kids.push(svgEl("path", { d: v.histPrice, fill: "none", stroke: "#211C16", "stroke-width": 2, "vector-effect": "non-scaling-stroke" }));
    setSvg(host, "0 0 1000 300", kids, { style: "width:100%;height:200px;display:block;" });

    // y-axis labels (overlay, positioned by percentage)
    const yLab = $("#hist-ylabels");
    yLab.innerHTML = "";
    v.histYTicks.forEach(t => {
      const s = document.createElement("span");
      s.className = "hist-ylabel";
      s.style.top = t.yp + "%";
      s.textContent = t.label;
      yLab.appendChild(s);
    });

    // episode markers (vertical dashed + numbered node)
    const marks = $("#hist-markers");
    marks.innerHTML = "";
    v.histEpisodes.forEach(e => {
      const line = document.createElement("div");
      line.className = "hist-marker-line";
      line.style.left = e.xp + "%";
      marks.appendChild(line);
      const node = document.createElement("div");
      node.className = "hist-marker-node";
      node.style.left = e.xp + "%";
      node.style.background = e.c;
      node.textContent = e.n;
      marks.appendChild(node);
    });

    // x-axis year labels
    const xLab = $("#hist-xlabels");
    xLab.innerHTML = "";
    v.histXTicks.forEach(t => {
      const s = document.createElement("span");
      s.textContent = t.label;
      xLab.appendChild(s);
    });

    // episode detail cards
    const cards = $("#hist-episode-cards");
    cards.innerHTML = "";
    v.histEpisodes.forEach(e => {
      const wrap = document.createElement("div");
      wrap.className = "ep-card";
      const badge = document.createElement("span");
      badge.className = "ep-badge";
      badge.style.background = e.c;
      badge.textContent = e.n;
      const txt = document.createElement("div");
      txt.innerHTML = '<div class="ep-title">' + e.label + '</div><div class="ep-sub">' + e.sub + "</div>";
      wrap.appendChild(badge);
      wrap.appendChild(txt);
      cards.appendChild(wrap);
    });
  }

  // axis label rows for the editorial price chart
  function renderPriceAxes(v) {
    const yLab = $("#price-ylabels");
    if (yLab) {
      yLab.innerHTML = "";
      v.priceTicks.forEach(t => {
        const s = document.createElement("span");
        s.className = "price-ylabel";
        s.textContent = t.label;
        yLab.appendChild(s);
      });
    }
    const xLab = $("#price-xlabels");
    if (xLab) {
      xLab.innerHTML = "";
      v.xTicks.forEach(t => {
        const s = document.createElement("span");
        s.textContent = t.label;
        xLab.appendChild(s);
      });
    }
  }

  // terminal price chart y-axis labels (top-left stack)
  function renderTermAxes(v) {
    const yLab = $("#t-price-ylabels");
    if (!yLab) return;
    yLab.innerHTML = "";
    v.priceTicks.forEach(t => {
      const s = document.createElement("span");
      s.textContent = t.label;
      yLab.appendChild(s);
    });
  }

  // ----------------------------------------------------------------------
  // wire-up
  // ----------------------------------------------------------------------
  function render() {
    const v = build();

    // crossing-moment caption
    const cap = $("#cross-caption-date");
    if (cap) cap.textContent = v.crLabel;

    // --- editorial ---
    renderPriceChart($("#price-chart"), v, {
      height: "210px", grid: "rgba(33,28,22,.08)",
      costSW: 2.5, costDash: "7 5", priceStroke: "#211C16", priceSW: 2.5,
      crossLine: true, dot: 5, dotStroke: "#F6F1E6"
    });
    renderPriceAxes(v);
    renderDonut($("#donut-lg"), v, {
      r: 80, sw: 20, viewBox: "0 0 230 230", cx: 115, cy: 115,
      dashLth: v.donutDashLth, dashSth: v.donutDashSth, off: v.donutOff
    });
    renderSupplyBand($("#supply-chart"), v, {
      height: "130px", lthFill: "rgba(62,107,134,.32)", sthFill: "rgba(232,81,42,.28)",
      lthStroke: "#3E6B86", lthSW: 2
    });
    renderHistory(v);

    // --- terminal ---
    renderPriceChart($("#t-price-chart"), v, {
      height: "340px", grid: "rgba(233,225,205,.05)",
      costSW: 2, costDash: "6 5", priceStroke: "#F1EBDB", priceSW: 1.5,
      crossLine: true, dot: 4.5, dotStroke: null
    });
    renderTermAxes(v);
    renderSupplyBand($("#t-supply-chart"), v, {
      height: "170px", lthFill: "rgba(110,145,168,.3)", sthFill: "rgba(232,81,42,.26)",
      lthStroke: "#6E91A8", lthSW: 1.5
    });

    // --- mobile / push showcase ---
    renderDonut($("#m-donut"), v, {
      r: 56, sw: 15, viewBox: "0 0 160 160", cx: 80, cy: 80,
      dashLth: v.donutDashLthSm, dashSth: v.donutDashSthSm, off: v.donutOffSm
    });
    renderPriceChart($("#m-price-chart"), v, {
      height: "120px", grid: null,
      costSW: 3, costDash: "10 7", priceStroke: "#211C16", priceSW: 3,
      crossLine: false, dot: 9, dotStroke: null
    });
  }

  function wireControls() {
    // view toggle (editorial / terminal)
    const tabs = document.querySelectorAll("[data-view-tab]");
    tabs.forEach(tab => {
      tab.addEventListener("click", () => {
        const view = tab.getAttribute("data-view-tab");
        tabs.forEach(t => t.classList.toggle("is-active", t === tab));
        document.querySelectorAll("[data-view]").forEach(panel => {
          panel.classList.toggle("is-hidden", panel.getAttribute("data-view") !== view);
        });
      });
    });

    // radar sweep animation toggle
    const sweep = $("#sweep-toggle");
    if (sweep) {
      const apply = () => document.body.classList.toggle("sweep-off", !sweep.checked);
      sweep.addEventListener("change", apply);
      apply();
    }
  }

  // 把真實資料(window.RADAR_DATA.latest)塞進 editorial 畫面的文字節點
  function syncText() {
    const D = window.RADAR_DATA;
    if (!D || !D.latest) return;
    const L = D.latest;
    const set = (id, text) => { const el = document.getElementById(id); if (el && text != null) el.textContent = text; };
    set("r-lede", L.headline);
    set("r-lthbtc", L.lth_btc_str);
    set("r-sthbtc", L.sth_btc_str);
    set("r-price", L.price_str);
    set("r-cost", L.cost_str);
    set("r-under", L.underwater_str);
    const donut = document.getElementById("r-donut");
    if (donut && L.lth_pct_str) donut.innerHTML = L.lth_pct_str.replace("%", "<span>%</span>");
    // 誠實標示:價格即時 vs 持有者結構截至某日(凍結)
    const M = D.meta || {};
    if (M.price_as_of) set("r-asof-price", "現價 " + M.price_as_of + " · 即時");
    if (M.cohort_as_of) set("r-asof-cohort", "持有者結構截至 " + M.cohort_as_of);
  }

  function init() {
    render();
    wireControls();
    syncText();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
