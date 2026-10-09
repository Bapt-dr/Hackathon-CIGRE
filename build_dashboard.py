#!/usr/bin/env python3
"""
build_dashboard.py
------------------
Lit le CSV horaire (séparateur ";", décimale ",") et génère index.html :
une page autonome et interactive (aucun serveur nécessaire).

Usage :
    python build_dashboard.py donnees_6_avril_2025.csv
"""
import sys
import json
from pathlib import Path

import pandas as pd

OUT_FILE = "index.html"


def load_rows(csv_path):
    df = pd.read_csv(csv_path, sep=";", decimal=",", encoding="utf-8-sig")
    df.columns = ["heure", "prix", "solaire", "eolien", "conso", "nuc"]
    heures = df["heure"].astype(str).str.extract(r"(\d+)")[0].astype(int)
    rows = []
    for h, p, s, e, c, n in zip(heures, df["prix"], df["solaire"],
                                df["eolien"], df["conso"], df["nuc"]):
        rows.append({
            "h": int(h), "prix": float(p), "solaire": float(s),
            "eolien": float(e), "conso": float(c), "nuc": float(n),
        })
    if len(rows) != 24:
        raise ValueError(f"Attendu 24 lignes horaires, trouvé {len(rows)}")
    return rows


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Batterie 2h — impact d'un parc français</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0a0a0a; --panel: #111; --border: #222; --text: #ddd; --muted: #777;
    --accent: #00d4aa; --kpi: #0d0d0d; --pos: #2ecc71; --neg: #e74c3c;
    box-sizing: border-box;
    padding-top: env(safe-area-inset-top, 0px);
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }
  body.light {
    --bg: #ffffff; --panel: #f5f6f7; --border: #d9dde2; --text: #222; --muted: #666;
    --accent: #008f73; --kpi: #ffffff; --pos: #1e8449; --neg: #c0392b;
  }
  body { margin: 0; background: var(--bg); color: var(--text); min-height: 100vh;
         font-family: Consolas, "Courier New", monospace; padding: 24px; }
  .top { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; }
  h1 { color: var(--accent); letter-spacing: 3px; font-size: 26px; margin: 0; }
  .sub { color: var(--muted); font-size: 13px; margin: 6px 0 20px; }
  select { background: var(--panel); color: var(--text); border: 1px solid var(--border);
           padding: 8px 10px; font-family: inherit; border-radius: 4px; }
  .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 5px;
           padding: 18px; margin-bottom: 20px; }
  .controls { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 24px; }
  label { color: var(--muted); font-size: 12px; display: flex; justify-content: space-between; }
  label b { color: var(--accent); font-size: 16px; }
  input[type=range] { width: 100%; accent-color: var(--accent); margin-top: 8px; }
  .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; }
  .kpi { background: var(--kpi); border: 1px solid var(--border); border-radius: 5px; padding: 14px; }
  .kpi .t { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
  .kpi .v { color: var(--accent); font-size: 22px; margin-top: 6px; }
  .kpi .s { color: var(--muted); font-size: 11px; margin-top: 4px; }
  .neg { color: var(--neg) !important; } .pos { color: var(--pos) !important; }
  .chart-box { position: relative; height: 340px; }
  .info { color: var(--muted); font-size: 12px; line-height: 1.6; }
  .info code { color: var(--text); }
  h2 { color: var(--accent); font-size: 15px; margin: 0 0 12px; letter-spacing: 1px; }
  .eq { color: var(--text); font-size: 13px; margin: 0 0 12px; }
  @media (max-width: 600px) { body { padding: 14px; } .chart-box { height: 280px; } }
</style>
</head>
<body>

<div class="top">
  <div>
    <h1>BATTERIE 2H — IMPACT D'UN PARC FRANÇAIS</h1>
    <p class="sub">Données horaires du 6 avril 2025 · Prix spot · Modèle prix = a·(solaire+éolien) + b</p>
  </div>
  <select id="theme" aria-label="Thème">
    <option value="dark">Fond noir</option>
    <option value="light">Fond blanc</option>
  </select>
</div>

<div class="panel">
  <div class="controls">
    <div>
      <label>Parc français (puissance, 2h) <b id="frVal"></b></label>
      <input type="range" id="fr" min="0" max="3" step="0.1" value="1.3">
    </div>
    <div>
      <label>Batterie étudiée (puissance, 2h) <b id="batVal"></b></label>
      <input type="range" id="bat" min="50" max="500" step="10" value="200">
    </div>
    <div>
      <label>Rendement aller-retour <b id="effVal"></b></label>
      <input type="range" id="eff" min="70" max="100" step="1" value="85">
    </div>
  </div>
</div>

<div class="panel">
  <div class="kpis">
    <div class="kpi"><div class="t">Revenu batterie (sans parc FR)</div>
      <div class="v" id="rev0"></div><div class="s">€ / jour</div></div>
    <div class="kpi"><div class="t">Revenu batterie (avec parc FR)</div>
      <div class="v" id="rev1"></div><div class="s">€ / jour</div></div>
    <div class="kpi"><div class="t">Impact sur la batterie</div>
      <div class="v" id="dRev"></div><div class="s" id="dRevPct"></div></div>
    <div class="kpi"><div class="t">Revenu du parc FR</div>
      <div class="v" id="revFr"></div><div class="s">€ / jour</div></div>
    <div class="kpi"><div class="t">Hausse max du prix</div>
      <div class="v" id="dPrixMax"></div><div class="s">€/MWh (heure de charge)</div></div>
  </div>
</div>

<div class="panel">
  <h2>PRIX SPOT : RÉEL vs APRÈS PARC FR</h2>
  <div class="chart-box"><canvas id="cPrix"></canvas></div>
</div>

<div class="panel">
  <h2>DISPATCH (MW) — + charge / − décharge</h2>
  <div class="chart-box"><canvas id="cDispatch"></canvas></div>
  <p class="info" id="planText"></p>
</div>

<div class="panel">
  <h2>RÉGRESSION : PRIX NÉGATIFS vs SOLAIRE + ÉOLIEN</h2>
  <p class="eq" id="regEq"></p>
  <div class="chart-box"><canvas id="cReg"></canvas></div>
  <p class="info">Régression calculée sur les heures à prix négatif uniquement. Le coefficient a sert à estimer l'impact du parc FR sur le prix.</p>
</div>

<div class="panel info">
  <h2>MÉTHODE</h2>
  Pour chaque puissance, l'algorithme choisit jusqu'à 2 heures de charge et jusqu'à 2 heures de décharge
  (1 h chacune, à pleine puissance) qui maximisent le revenu, en respectant
  l'état de charge (on ne décharge pas plus que ce qui a été stocké).
  Le rendement aller-retour est appliqué à la charge : pour 1 MWh soutiré, η·1 MWh est stocké.
  Le parc FR agit comme un preneur de prix sur les prix réels, puis son impact sur le prix est
  <code>Δprix = −a × puissance</code>, où <code>a</code> est la pente de la régression
  prix = a·(solaire+éolien)+b calculée sur les heures à prix négatif.
  La batterie étudiée est redispatchée sur les prix résultant de l'impact du parc FR.
  Pas de dégradation ni de coûts fixes dans ce modèle.
</div>

<script>
const RAW = __DATA__;

// ---------- Régression prix = a·(solaire+éolien) + b (heures à prix négatif) ----------
function fitLine(xs, ys) {
  const n = xs.length;
  if (n < 2) return { a: 0, b: 0, r2: 0 };
  const mx = xs.reduce((s, v) => s + v, 0) / n;
  const my = ys.reduce((s, v) => s + v, 0) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) {
    sxy += (xs[i] - mx) * (ys[i] - my);
    sxx += (xs[i] - mx) ** 2;
    syy += (ys[i] - my) ** 2;
  }
  const a = sxx === 0 ? 0 : sxy / sxx;
  const r2 = (sxx === 0 || syy === 0) ? 0 : (sxy * sxy) / (sxx * syy);
  return { a, b: my - a * mx, r2 };
}
const neg = RAW.filter(r => r.prix < 0);
const REG = fitLine(neg.map(r => r.solaire + r.eolien), neg.map(r => r.prix));
const A = REG.a;

// ---------- Dispatch optimal ----------
// Charge : jusqu'à 2 heures à pleine puissance P (soutirage réseau P, stockage η·P)
// Décharge : jusqu'à 2 heures à pleine puissance P (injection P, stockage -P)
// Contrainte : l'état de charge reste entre 0 et 2P à chaque heure.
function allSets(n) {
  const s = [];
  for (let i = 0; i < n; i++) { s.push([i]); for (let j = i + 1; j < n; j++) s.push([i, j]); }
  return s;
}
const SETS = allSets(24);

function bestDispatch(prices, P, eta) {
  const n = prices.length;
  const profile = new Array(n).fill(0);
  if (P <= 0) return { profile, rev: 0, charge: [], discharge: [] };
  let best = { c: [], d: [] }, bestRev = 0;
  for (const c of SETS) {
    const cCost = P * c.reduce((s, h) => s + prices[h], 0);
    for (const d of SETS) {
      if (d.some(h => c.includes(h))) continue;
      const rev = P * d.reduce((s, h) => s + prices[h], 0) - cCost;
      if (rev <= bestRev) continue;
      let soc = 0, ok = true;
      for (let h = 0; h < n; h++) {
        if (c.includes(h)) soc += eta * P;
        if (d.includes(h)) soc -= P;
        if (soc < -1e-9 || soc > 2 * P + 1e-9) { ok = false; break; }
      }
      if (!ok) continue;
      bestRev = rev; best = { c, d };
    }
  }
  best.c.forEach(h => profile[h] = P);
  best.d.forEach(h => profile[h] = -P);
  return { profile, rev: bestRev, charge: best.c, discharge: best.d };
}

// Revenu (€) d'un profil de puissance sur des prix horaires (pas 1 h)
function revenue(prices, profile) {
  let r = 0;
  for (let h = 0; h < prices.length; h++) r -= prices[h] * profile[h];
  return r;
}

const fmtEur = v => Math.round(v).toLocaleString("fr-FR") + " €";
const hours = RAW.map(r => r.h + "h");
const basePrix = RAW.map(r => r.prix);

// ---------- Thème ----------
const THEMES = {
  dark:  { text: "#aaaaaa", grid: "#1a1a1a" },
  light: { text: "#333333", grid: "#e3e3e3" },
};
let currentTheme = "dark";
function applyTheme(t) {
  currentTheme = t;
  document.body.classList.toggle("light", t === "light");
  const c = THEMES[t];
  [cPrix, cDispatch, cReg].forEach(ch => {
    const o = ch.options;
    o.plugins.legend.labels.color = c.text;
    Object.values(o.scales).forEach(s => {
      s.ticks.color = c.text;
      s.grid.color = c.grid;
      if (s.title) s.title.color = c.text;
    });
    ch.update();
  });
}

// ---------- Graphiques ----------
const axisOpts = (xTitle, yTitle) => ({
  x: { ticks: { color: THEMES.dark.text }, grid: { color: THEMES.dark.grid },
       title: { display: !!xTitle, text: xTitle || "", color: THEMES.dark.text } },
  y: { ticks: { color: THEMES.dark.text }, grid: { color: THEMES.dark.grid },
       title: { display: !!yTitle, text: yTitle || "", color: THEMES.dark.text } },
});
const legendOpts = { labels: { color: THEMES.dark.text } };

const cPrix = new Chart(document.getElementById("cPrix"), {
  type: "line",
  data: { labels: hours, datasets: [
    { label: "Prix réel (€/MWh)", data: basePrix, borderColor: "#1f8bd6",
      backgroundColor: "#1f8bd6", tension: 0.2, pointRadius: 3 },
    { label: "Prix après parc FR (€/MWh)", data: basePrix, borderColor: "#e8731c",
      backgroundColor: "#e8731c", borderDash: [6, 4], tension: 0.2, pointRadius: 3 },
  ]},
  options: { responsive: true, maintainAspectRatio: false,
    plugins: { legend: legendOpts }, scales: axisOpts("", "€/MWh") },
});

const cDispatch = new Chart(document.getElementById("cDispatch"), {
  type: "bar",
  data: { labels: hours, datasets: [
    { label: "Parc FR (MW)", data: [], backgroundColor: "#e8731c" },
    { label: "Batterie étudiée (MW)", data: [], backgroundColor: "#2ecc71" },
  ]},
  options: { responsive: true, maintainAspectRatio: false,
    plugins: { legend: legendOpts }, scales: axisOpts("", "MW") },
});

// Régression : points des heures à prix négatif + droite ajustée
const regPts = neg.map(r => ({ x: r.solaire + r.eolien, y: r.prix, h: r.h }));
const xMin = regPts.length ? Math.min(...regPts.map(p => p.x)) : 0;
const xMax = regPts.length ? Math.max(...regPts.map(p => p.x)) : 1;
const cReg = new Chart(document.getElementById("cReg"), {
  type: "scatter",
  data: { datasets: [
    { label: "Heures à prix négatif", data: regPts,
      backgroundColor: "#1f8bd6", pointRadius: 6 },
    { label: "Régression linéaire", type: "line", showLine: true,
      data: [{ x: xMin, y: REG.a * xMin + REG.b }, { x: xMax, y: REG.a * xMax + REG.b }],
      borderColor: "#e8731c", backgroundColor: "#e8731c", borderWidth: 2, pointRadius: 0 },
  ]},
  options: { responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: legendOpts,
      tooltip: { callbacks: { label: ctx => ctx.raw.h === undefined
        ? "Régression"
        : `${ctx.raw.h}h : ${Math.round(ctx.raw.x)} MW, ${ctx.raw.y.toFixed(1)} €/MWh` } },
    },
    scales: axisOpts("Solaire + éolien (MW)", "Prix (€/MWh)") },
});
document.getElementById("regEq").textContent =
  `prix = ${REG.a.toFixed(5)} × (solaire + éolien) + ${REG.b.toFixed(1)}   |   R² = ${REG.r2.toFixed(2)}   |   ${neg.length} heures à prix négatif`;

// ---------- Mise à jour à chaque mouvement de slider ----------
function update() {
  const frGW = parseFloat(document.getElementById("fr").value);
  const batMW = parseFloat(document.getElementById("bat").value);
  const eta = parseFloat(document.getElementById("eff").value) / 100;
  document.getElementById("frVal").textContent = frGW.toFixed(1) + " GW";
  document.getElementById("batVal").textContent = batMW + " MW";
  document.getElementById("effVal").textContent = Math.round(eta * 100) + " %";

  const Pfr = frGW * 1000;
  const fr = bestDispatch(basePrix, Pfr, eta);
  const prixFR = basePrix.map((p, h) => p - A * fr.profile[h]);
  const bat0 = bestDispatch(basePrix, batMW, eta);
  const bat1 = bestDispatch(prixFR, batMW, eta);
  const rev0 = revenue(basePrix, bat0.profile);
  const rev1 = revenue(prixFR, bat1.profile);
  const revFr = revenue(prixFR, fr.profile);
  const dRev = rev1 - rev0;
  const dPrixMax = Math.max(...prixFR.map((p, h) => p - basePrix[h]));

  document.getElementById("rev0").textContent = fmtEur(rev0);
  document.getElementById("rev1").textContent = fmtEur(rev1);
  const dEl = document.getElementById("dRev");
  dEl.textContent = (dRev >= 0 ? "+" : "") + fmtEur(dRev);
  dEl.className = "v " + (dRev >= 0 ? "pos" : "neg");
  document.getElementById("dRevPct").textContent =
    rev0 !== 0 ? ((dRev / Math.abs(rev0)) * 100).toFixed(1) + " % vs sans parc FR" : "";
  document.getElementById("revFr").textContent = fmtEur(revFr);
  document.getElementById("dPrixMax").textContent = "+" + dPrixMax.toFixed(1) + " €/MWh";

  cPrix.data.datasets[1].data = prixFR;
  cPrix.update();
  cDispatch.data.datasets[0].data = fr.profile;
  cDispatch.data.datasets[1].data = bat1.profile;
  cDispatch.update();

  const lbl = arr => arr.map(h => h + "h").join(", ") || "—";
  document.getElementById("planText").textContent =
    `Parc FR : charge ${lbl(fr.charge)} — décharge ${lbl(fr.discharge)}.   ` +
    `Batterie : charge ${lbl(bat1.charge)} — décharge ${lbl(bat1.discharge)}.`;
}

document.getElementById("fr").addEventListener("input", update);
document.getElementById("bat").addEventListener("input", update);
document.getElementById("eff").addEventListener("input", update);
document.getElementById("theme").addEventListener("change", e => applyTheme(e.target.value));

applyTheme("dark");
update();
</script>
</body>
</html>
"""


def main():
    if len(sys.argv) < 2:
        print("Usage : python build_dashboard.py donnees_6_avril_2025.csv")
        sys.exit(1)
    rows = load_rows(sys.argv[1])
    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(rows, ensure_ascii=False))
    Path(OUT_FILE).write_text(html, encoding="utf-8")
    print(f"OK -> {OUT_FILE} ({len(rows)} heures)")


if __name__ == "__main__":
    main()
