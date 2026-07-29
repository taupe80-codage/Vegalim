#!/usr/bin/env python3
"""Genere le HTML de l'artifact interactif 'Recettes ALIM' (recherche,
filtres, alertes qualite, detection de doublons, comparaison cote a cote,
suppression, regroupement pour analyse, renommage) a partir de
recipe_list.json (lui-meme genere par extract_recipe_list.py).

Usage:
    python build_recipe_list_artifact.py [chemin_de_sortie.html]

Si aucun chemin n'est fourni, ecrit recipe_list_artifact.html a cote de
recipe_list.json (dans backend/data/recipes/). Ce fichier HTML n'est PAS
destine a etre committe : c'est un artefact jetable a republier via l'outil
Artifact. Le fichier de revue durable est recipe_list.md.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "recipe_list.json"
DEFAULT_OUT = ROOT / "recipe_list_artifact.html"

data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
data_json = json.dumps(data, ensure_ascii=False)

html = """<meta charset="utf-8">
<title>Recettes ALIM — liste et sélection</title>
<style>
:root {
  --bg: #FAF8F3;
  --surface: #FFFFFF;
  --surface-2: #F1EEE5;
  --text: #24261F;
  --text-dim: #6B6D5F;
  --border: #DDD9CC;
  --accent: #4C6B41;
  --accent-ink: #FFFFFF;
  --accent-soft: #E7EDE1;
  --link: #3C6E9E;
  --link-ink: #FFFFFF;
  --link-soft: #E3ECF3;
  --danger: #A8402E;
  --danger-soft: #F5E4DF;
  --danger-ink: #FFFFFF;
  --warn: #9A6A17;
  --warn-soft: #F6EBD6;
  --dup: #7A4FA3;
  --dup-soft: #EFE5F5;
  --focus: #2F6FED;
}
:root[data-theme="dark"] {
  --bg: #191B14;
  --surface: #21231A;
  --surface-2: #292B20;
  --text: #EDEBE1;
  --text-dim: #9B9C8C;
  --border: #34362A;
  --accent: #8FB37D;
  --accent-ink: #14200F;
  --accent-soft: #29331F;
  --link: #7FAFDA;
  --link-ink: #10202E;
  --link-soft: #202B33;
  --danger: #D97A63;
  --danger-soft: #3A241D;
  --danger-ink: #1E120D;
  --warn: #E0B25A;
  --warn-soft: #3A2E14;
  --dup: #C7A6E0;
  --dup-soft: #2E2438;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #191B14;
    --surface: #21231A;
    --surface-2: #292B20;
    --text: #EDEBE1;
    --text-dim: #9B9C8C;
    --border: #34362A;
    --accent: #8FB37D;
    --accent-ink: #14200F;
    --accent-soft: #29331F;
    --link: #7FAFDA;
    --link-ink: #10202E;
    --link-soft: #202B33;
    --danger: #D97A63;
    --danger-soft: #3A241D;
    --danger-ink: #1E120D;
    --warn: #E0B25A;
    --warn-soft: #3A2E14;
    --dup: #C7A6E0;
    --dup-soft: #2E2438;
  }
}

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  font-size: 14.5px;
  line-height: 1.45;
  min-height: 100vh;
}

.wrap {
  max-width: 980px;
  margin: 0 auto;
  padding: 0 20px 140px;
}

header.top {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--bg);
  padding: 26px 0 12px;
  border-bottom: 1px solid var(--border);
}

h1 {
  font-family: Georgia, "Iowan Old Style", "Palatino Linotype", serif;
  font-weight: 400;
  font-size: 25px;
  letter-spacing: 0.2px;
  margin: 0 0 4px;
  text-wrap: balance;
}

.subhead {
  color: var(--text-dim);
  font-size: 13px;
  margin: 0 0 4px;
}
.subhead .count { font-variant-numeric: tabular-nums; color: var(--text); font-weight: 600; }

.stats {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--text-dim);
  margin: 0 0 12px;
}
.stats b { font-variant-numeric: tabular-nums; color: var(--text); }
.stats .warn-stat b { color: var(--warn); }
.stats .dup-stat b { color: var(--dup); }

.controls {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.search-box {
  position: relative;
  flex: 1 1 220px;
  min-width: 160px;
}
.search-box svg {
  position: absolute;
  left: 11px;
  top: 50%;
  transform: translateY(-50%);
  width: 15px;
  height: 15px;
  stroke: var(--text-dim);
  pointer-events: none;
}
input[type="search"], input[type="text"] {
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 9px 12px;
  font-size: 14px;
  color: var(--text);
  outline: none;
  font-family: inherit;
}
input[type="search"] { padding-left: 32px; }
input[type="search"]:focus-visible, input[type="text"]:focus-visible {
  border-color: var(--focus);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--focus) 22%, transparent);
}
input[type="search"]::-webkit-search-cancel-button { cursor: pointer; }

select.filter {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 9px 10px;
  font-size: 13px;
  color: var(--text);
  font-family: inherit;
  cursor: pointer;
  max-width: 160px;
}
select.filter:focus-visible { border-color: var(--focus); box-shadow: 0 0 0 3px color-mix(in srgb, var(--focus) 22%, transparent); }

.flag-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--text-dim);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
  cursor: pointer;
  white-space: nowrap;
}
.flag-toggle input { cursor: pointer; }
.flag-toggle.active-warn { border-color: var(--warn); color: var(--warn); background: var(--warn-soft); }
.flag-toggle.active-dup { border-color: var(--dup); color: var(--dup); background: var(--dup-soft); }

.btn {
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  border-radius: 8px;
  padding: 9px 13px;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  white-space: nowrap;
}
.btn:hover { background: var(--surface-2); }
.btn:disabled { opacity: 0.45; cursor: not-allowed; }
.btn:focus-visible { outline: none; border-color: var(--focus); box-shadow: 0 0 0 3px color-mix(in srgb, var(--focus) 22%, transparent); }

.mode-toggle {
  display: inline-flex;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}
.mode-toggle button {
  border: none;
  background: var(--surface);
  color: var(--text-dim);
  padding: 9px 13px;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
}
.mode-toggle button + button { border-left: 1px solid var(--border); }
.mode-toggle button.active.mode-del { background: var(--danger-soft); color: var(--danger); font-weight: 600; }
.mode-toggle button.active.mode-link { background: var(--link-soft); color: var(--link); font-weight: 600; }
.mode-toggle button.active.mode-compare { background: var(--dup-soft); color: var(--dup); font-weight: 600; }
.mode-toggle button:focus-visible { outline: none; box-shadow: inset 0 0 0 2px var(--focus); }

.link-toolbar, .compare-toolbar {
  display: none;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  flex-wrap: wrap;
}
.link-toolbar { background: var(--link-soft); border: 1px solid var(--link); }
.compare-toolbar { background: var(--dup-soft); border: 1px solid var(--dup); }
.link-toolbar.show, .compare-toolbar.show { display: flex; }
.link-toolbar .lbl { font-size: 13px; color: var(--link); white-space: nowrap; }
.compare-toolbar .lbl { font-size: 13px; color: var(--dup); white-space: nowrap; }
.link-toolbar .lbl .n, .compare-toolbar .lbl .n { font-variant-numeric: tabular-nums; font-weight: 700; }
.link-toolbar input[type="text"] { flex: 1 1 160px; min-width: 140px; }
.btn-compare { background: var(--dup); color: white; border: 1px solid var(--dup); }
.btn-compare:hover { filter: brightness(1.08); }
.btn-compare:disabled { background: var(--surface); color: var(--text-dim); border-color: var(--border); }

.groups-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 10px;
}
.group-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--link-soft);
  color: var(--link);
  border-radius: 6px;
  padding: 4px 6px 4px 10px;
  font-size: 12px;
}
.group-chip .x {
  background: none;
  border: none;
  color: var(--link);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 2px 4px;
  opacity: 0.7;
}
.group-chip .x:hover { opacity: 1; }

.jump {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  margin-top: 12px;
  font-size: 11px;
}
.jump a {
  color: var(--text-dim);
  text-decoration: none;
  padding: 2px 5px;
  border-radius: 4px;
  font-variant-caps: all-small-caps;
  letter-spacing: 0.03em;
}
.jump a:hover, .jump a:focus-visible { background: var(--accent-soft); color: var(--accent); outline: none; }
.jump a.disabled { opacity: 0.28; pointer-events: none; }

.no-results {
  color: var(--text-dim);
  text-align: center;
  padding: 60px 20px;
  font-size: 14px;
  display: none;
}
.no-results.show { display: block; }

.letter-group { margin-top: 6px; }
.letter-head {
  position: sticky;
  background: var(--bg);
  font-family: Georgia, serif;
  font-size: 13px;
  color: var(--accent);
  font-weight: 700;
  padding: 10px 4px 4px;
  z-index: 5;
}

ul.list { list-style: none; margin: 0; padding: 0; }

li.row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 9px 6px;
  border-bottom: 1px solid var(--border);
}
li.row:hover { background: var(--surface-2); }
li.row.marked { background: var(--danger-soft); }
li.row.pending-link { background: var(--link-soft); }
li.row.pending-compare { background: var(--dup-soft); }

.chk {
  appearance: none;
  -webkit-appearance: none;
  width: 17px;
  height: 17px;
  border: 1.5px solid var(--border);
  border-radius: 4px;
  background: var(--surface);
  flex: 0 0 17px;
  margin-top: 2px;
  cursor: pointer;
  position: relative;
}
.chk.mode-del:checked { background: var(--danger); border-color: var(--danger); }
.chk.mode-del:checked::after { border-color: var(--danger-ink); }
.chk.mode-link:checked { background: var(--link); border-color: var(--link); }
.chk.mode-link:checked::after { border-color: var(--link-ink); }
.chk.mode-compare:checked { background: var(--dup); border-color: var(--dup); }
.chk.mode-compare:checked::after { border-color: white; }
.chk:checked::after {
  content: "";
  position: absolute;
  left: 4.5px;
  top: 1.5px;
  width: 5px;
  height: 9px;
  border-style: solid;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}
.chk:focus-visible { outline: none; box-shadow: 0 0 0 3px color-mix(in srgb, var(--focus) 22%, transparent); }

.row-main { flex: 1; min-width: 0; cursor: pointer; }
.row-title-line { display: flex; align-items: center; gap: 6px; }
.row-title {
  font-size: 14.5px;
  color: var(--text);
}
li.row.marked .row-title { text-decoration: line-through; color: var(--text-dim); }
.row-title.old-title { color: var(--text-dim); font-size: 12.5px; text-decoration: line-through; }

.edit-btn {
  border: none;
  background: none;
  padding: 2px;
  cursor: pointer;
  color: var(--text-dim);
  opacity: 0;
  flex: 0 0 auto;
  display: flex;
}
li.row:hover .edit-btn, .edit-btn:focus-visible { opacity: 1; outline: none; }
.edit-btn svg { width: 13px; height: 13px; stroke: currentColor; }
.edit-btn:hover { color: var(--accent); }

.rename-input {
  font-size: 14.5px;
  padding: 3px 6px;
  max-width: 340px;
}

.row-meta {
  display: flex;
  gap: 6px;
  margin-top: 3px;
  flex-wrap: wrap;
  align-items: center;
}
.tag {
  font-size: 10.5px;
  color: var(--text-dim);
  background: var(--surface-2);
  border-radius: 4px;
  padding: 1px 6px;
  font-variant-caps: all-small-caps;
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.tag.vegan { color: var(--accent); background: var(--accent-soft); }
.tag.del { color: var(--danger); background: var(--danger-soft); }
.tag.link { color: var(--link); background: var(--link-soft); }
.tag.renamed { color: var(--link); background: var(--link-soft); }
.tag.warn { color: var(--warn); background: var(--warn-soft); }
.tag.dup {
  color: var(--dup);
  background: var(--dup-soft);
  border: none;
  cursor: pointer;
  font: inherit;
  font-variant-caps: all-small-caps;
  letter-spacing: 0.02em;
}
.tag.dup:hover { filter: brightness(0.95); text-decoration: underline; }
.row-id {
  font-size: 10.5px;
  color: var(--text-dim);
  font-family: ui-monospace, "SF Mono", Consolas, monospace;
  opacity: 0.65;
}

mark {
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: 2px;
  padding: 0 1px;
}

.bottombar {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  display: flex;
  justify-content: center;
  pointer-events: none;
  padding: 16px;
  z-index: 20;
}
.bottombar-inner {
  pointer-events: auto;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 8px 28px rgba(0,0,0,0.18);
  padding: 10px 12px 10px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  transform: translateY(120%);
  transition: transform 0.22s ease;
  max-width: calc(100vw - 32px);
}
.bottombar-inner.show { transform: translateY(0); }
.bottombar-count {
  font-size: 13px;
  white-space: nowrap;
  display: flex;
  gap: 10px;
}
.bottombar-count b { font-variant-numeric: tabular-nums; }
.bottombar-count .del-n b { color: var(--danger); }
.bottombar-count .link-n b { color: var(--link); }
.bottombar-count .ren-n b { color: var(--accent); }
.btn-primary {
  background: var(--text);
  color: var(--bg);
  border: 1px solid var(--text);
}
.btn-primary:hover { filter: brightness(1.15); }
.btn-link {
  background: var(--link);
  color: var(--link-ink);
  border: 1px solid var(--link);
}
.btn-link:hover { filter: brightness(1.08); }
.btn-ghost {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-dim);
}

.toast {
  position: fixed;
  bottom: 92px;
  left: 50%;
  transform: translateX(-50%) translateY(8px);
  background: var(--text);
  color: var(--bg);
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.18s ease, transform 0.18s ease;
  z-index: 30;
  white-space: nowrap;
  max-width: calc(100vw - 32px);
  text-overflow: ellipsis;
  overflow: hidden;
}
.toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }

.modal-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.45);
  z-index: 40;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.modal-overlay.show { display: flex; }
.modal-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  max-width: 640px;
  width: 100%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 12px 36px rgba(0,0,0,0.25);
}
.modal-box.wide { max-width: min(1400px, calc(100vw - 40px)); }
.modal-box h2 {
  font-family: Georgia, serif;
  font-weight: 400;
  font-size: 18px;
  margin: 0;
}
.modal-box p {
  margin: 0;
  color: var(--text-dim);
  font-size: 13px;
}
.modal-box textarea {
  flex: 1;
  min-height: 260px;
  resize: vertical;
  background: var(--surface-2);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px;
  font-family: ui-monospace, "SF Mono", Consolas, monospace;
  font-size: 12px;
  line-height: 1.5;
}
.modal-box textarea:focus-visible {
  outline: none;
  border-color: var(--focus);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--focus) 22%, transparent);
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.compare-row {
  display: flex;
  gap: 14px;
  overflow-x: auto;
  padding-bottom: 6px;
}
.compare-card {
  flex: 0 0 260px;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px;
  background: var(--surface-2);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.compare-card h3 {
  font-family: Georgia, serif;
  font-weight: 400;
  font-size: 15px;
  margin: 0;
  line-height: 1.3;
}
.compare-line {
  font-size: 12px;
  color: var(--text-dim);
}
.compare-line b { color: var(--text); font-variant-numeric: tabular-nums; }
.compare-chips { display: flex; flex-wrap: wrap; gap: 4px; }
.compare-desc {
  font-size: 12.5px;
  color: var(--text);
  font-style: italic;
  line-height: 1.4;
}
.compare-compo {
  font-size: 12px;
  border-top: 1px solid var(--border);
  padding-top: 8px;
  margin: 0;
}
.compare-compo table { width: 100%; border-collapse: collapse; }
.compare-compo td { padding: 2px 0; vertical-align: top; }
.compare-compo td.qty { color: var(--text-dim); text-align: right; white-space: nowrap; padding-left: 6px; font-variant-numeric: tabular-nums; }
.compare-remove {
  align-self: flex-end;
  border: none;
  background: none;
  color: var(--text-dim);
  cursor: pointer;
  font-size: 12px;
  padding: 2px 4px;
}
.compare-remove:hover { color: var(--danger); }

@media (max-width: 480px) {
  h1 { font-size: 21px; }
  .row-id { display: none; }
}
</style>

<div class="wrap">
  <header class="top">
    <h1>Recettes ALIM</h1>
    <p class="subhead"><span class="count" id="visibleCount">__TOTAL__</span> / __TOTAL__ recettes</p>
    <p class="stats" id="statsLine"></p>
    <div class="controls">
      <div class="search-box">
        <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <input type="search" id="search" placeholder="Rechercher un titre, une cuisine, un id…" autocomplete="off">
      </div>
      <select class="filter" id="filterDiet"><option value="">Tous régimes</option></select>
      <select class="filter" id="filterCuisine"><option value="">Toutes cuisines</option></select>
      <select class="filter" id="filterType"><option value="">Tous types</option></select>
      <label class="flag-toggle" id="toggleWarnLbl">
        <input type="checkbox" id="toggleWarn"> ⚠ Alertes seulement
      </label>
      <label class="flag-toggle" id="toggleDupLbl">
        <input type="checkbox" id="toggleDup"> 🔁 Doublons seulement
      </label>
      <div class="mode-toggle">
        <button type="button" id="modeDelBtn" class="active mode-del">Suppression</button>
        <button type="button" id="modeLinkBtn" class="mode-link">Lier pour analyse</button>
        <button type="button" id="modeCompareBtn" class="mode-compare">Comparer</button>
      </div>
    </div>

    <div class="link-toolbar" id="linkToolbar">
      <span class="lbl"><span class="n" id="pendingLinkCount">0</span> sélectionnée(s) pour ce groupe</span>
      <input type="text" id="groupNote" placeholder="Note pour Claude (optionnel) — ex. « composition suspecte »">
      <button class="btn btn-link" id="saveGroupBtn" disabled>Enregistrer le groupe</button>
      <button class="btn btn-ghost" id="clearPendingBtn">Annuler</button>
    </div>
    <div class="compare-toolbar" id="compareToolbar">
      <span class="lbl"><span class="n" id="compareCount">0</span> / 6 sélectionnée(s) pour comparaison</span>
      <button class="btn btn-compare" id="openCompareBtn" disabled>Comparer</button>
      <button class="btn btn-ghost" id="clearCompareBtn">Annuler</button>
    </div>
    <div class="groups-list" id="groupsList"></div>

    <nav class="jump" id="jump"></nav>
  </header>

  <div class="no-results" id="noResults">Aucune recette ne correspond à cette recherche.</div>
  <div id="listRoot"></div>
</div>

<div class="bottombar">
  <div class="bottombar-inner" id="bottombar">
    <span class="bottombar-count" id="bottombarCounts"></span>
    <button class="btn btn-primary" id="copyBtn">Copier tout pour Claude</button>
    <button class="btn btn-ghost" id="clearAllBtn">Tout effacer</button>
  </div>
</div>

<div class="toast" id="toast"></div>

<div class="modal-overlay" id="copyModal">
  <div class="modal-box">
    <h2>Copier pour Claude</h2>
    <p id="copyModalHint">La copie automatique a été bloquée par le navigateur. Cliquez dans la zone ci-dessous (le texte est déjà sélectionné) et faites Ctrl+C (ou Cmd+C sur Mac).</p>
    <textarea id="copyModalText" readonly></textarea>
    <div class="modal-actions">
      <button class="btn" id="copyModalRetry">Réessayer la copie auto</button>
      <button class="btn btn-primary" id="copyModalClose">Fermer</button>
    </div>
  </div>
</div>

<div class="modal-overlay" id="compareModal">
  <div class="modal-box wide">
    <h2>Comparaison</h2>
    <p>Compare la composition, les portions, le temps, le régime et la confiance des recettes sélectionnées.</p>
    <div class="compare-row" id="compareRow"></div>
    <div class="modal-actions">
      <button class="btn" id="copyCompareBtn">Copier la comparaison pour Claude</button>
      <button class="btn btn-primary" id="compareModalClose">Fermer</button>
    </div>
  </div>
</div>

<script>
const DATA = __DATA_JSON__;
const BY_ID = Object.fromEntries(DATA.map(r => [r.id, r]));

const DIET_LABELS = {
  vegan: 'vegan', vegetarian: 'végétarien', gluten_free: 'sans gluten',
  lactose_free: 'sans lactose', nut_free: 'sans fruits à coque',
  high_protein: 'riche en protéines', low_calorie: 'faible calories',
  kid_friendly: 'enfants', diabetes_friendly: 'diabète', raw: 'cru',
};
const FLAG_LABELS = {
  no_instructions: 'instructions manquantes',
  no_description: 'description manquante',
  no_composition: 'composition vide',
  low_confidence: 'confiance faible',
};

let mode = 'del'; // 'del' | 'link' | 'compare'
const marked = new Set();      // ids marqués pour suppression
const pendingLink = new Set(); // ids en cours de selection pour un groupe (non persiste)
const groups = [];             // { note, ids: [] }
const renamed = new Map();     // id -> { oldTitle, newTitle }
const compareSet = new Set();  // ids selectionnes pour comparaison (non persiste)
const MAX_COMPARE = 6;

// ── Sauvegarde automatique (localStorage) ─────────────────────────────────
// pendingLink et compareSet ne sont pas persistes : ce sont des selections
// en cours, ephemeres.
const STORAGE_KEY = 'alim_recipe_list_state_v1';

function saveState() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      marked: Array.from(marked),
      groups: groups,
      renamed: Array.from(renamed.entries()),
      savedAt: new Date().toISOString(),
    }));
  } catch (e) { /* stockage indisponible (mode prive, quota...) - on continue sans persister */ }
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return false;
    const state = JSON.parse(raw);
    (state.marked || []).forEach(id => marked.add(id));
    (state.groups || []).forEach(g => groups.push(g));
    (state.renamed || []).forEach(([id, v]) => renamed.set(id, v));
    return (state.marked || []).length > 0 || (state.groups || []).length > 0 || (state.renamed || []).length > 0;
  } catch (e) { return false; }
}

const listRoot = document.getElementById('listRoot');
const searchInput = document.getElementById('search');
const filterDiet = document.getElementById('filterDiet');
const filterCuisine = document.getElementById('filterCuisine');
const filterType = document.getElementById('filterType');
const toggleWarn = document.getElementById('toggleWarn');
const toggleDup = document.getElementById('toggleDup');
const toggleWarnLbl = document.getElementById('toggleWarnLbl');
const toggleDupLbl = document.getElementById('toggleDupLbl');
const visibleCountEl = document.getElementById('visibleCount');
const statsLineEl = document.getElementById('statsLine');
const noResultsEl = document.getElementById('noResults');
const jumpEl = document.getElementById('jump');
const bottombar = document.getElementById('bottombar');
const bottombarCounts = document.getElementById('bottombarCounts');
const toastEl = document.getElementById('toast');
const modeDelBtn = document.getElementById('modeDelBtn');
const modeLinkBtn = document.getElementById('modeLinkBtn');
const modeCompareBtn = document.getElementById('modeCompareBtn');
const linkToolbar = document.getElementById('linkToolbar');
const compareToolbar = document.getElementById('compareToolbar');
const pendingLinkCountEl = document.getElementById('pendingLinkCount');
const compareCountEl = document.getElementById('compareCount');
const openCompareBtn = document.getElementById('openCompareBtn');
const groupNoteInput = document.getElementById('groupNote');
const saveGroupBtn = document.getElementById('saveGroupBtn');
const groupsListEl = document.getElementById('groupsList');

function normalize(s) {
  return (s || '').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '');
}
function escapeHtml(s) {
  return (s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function currentTitle(r) {
  return renamed.has(r.id) ? renamed.get(r.id).newTitle : r.title;
}
function highlight(text, q) {
  if (!q) return escapeHtml(text);
  const norm = normalize(text);
  const nq = normalize(q);
  const idx = norm.indexOf(nq);
  if (idx === -1) return escapeHtml(text);
  return escapeHtml(text.slice(0, idx)) + '<mark>' + escapeHtml(text.slice(idx, idx + q.length)) + '</mark>' + escapeHtml(text.slice(idx + q.length));
}
function letterOf(title) {
  const c = normalize(title).trim().charAt(0).toUpperCase();
  return /[A-Z]/.test(c) ? c : '#';
}

const ALPHABET = '#ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
const availableLetters = new Set(DATA.map(r => letterOf(r.title)));

// ── Filtres dynamiques (peuples depuis les donnees reelles) ───────────────
function populateSelect(select, values, mapLabel) {
  const sorted = Array.from(values).sort((a, b) => (mapLabel ? mapLabel(a) : a).localeCompare(mapLabel ? mapLabel(b) : b));
  for (const v of sorted) {
    const opt = document.createElement('option');
    opt.value = v;
    opt.textContent = mapLabel ? mapLabel(v) : v;
    select.appendChild(opt);
  }
}
populateSelect(filterDiet, new Set(DATA.flatMap(r => r.diet || [])), v => DIET_LABELS[v] || v);
populateSelect(filterCuisine, new Set(DATA.map(r => r.cuisine).filter(Boolean)), v => v.replace(/_/g, ' '));
populateSelect(filterType, new Set(DATA.map(r => r.dish_type).filter(Boolean)));

function buildJumpNav() {
  jumpEl.innerHTML = ALPHABET.map(l => {
    const has = availableLetters.has(l);
    return `<a href="#letter-${l === '#' ? 'hash' : l}" class="${has ? '' : 'disabled'}">${l}</a>`;
  }).join('');
}

function groupsForId(id) {
  const idxs = [];
  groups.forEach((g, i) => { if (g.ids.includes(id)) idxs.push(i + 1); });
  return idxs;
}

function renderStats() {
  const nWarn = DATA.filter(r => (r.flags || []).length > 0).length;
  const nDup = DATA.filter(r => (r.similar || []).length > 0).length;
  statsLineEl.innerHTML =
    `<span>${DATA.length} recettes</span>` +
    `<span class="warn-stat">${nWarn} avec <b>${nWarn}</b> alerte(s) qualité</span>` +
    `<span class="dup-stat">${nDup} avec doublon <b>potentiel</b></span>`;
}

function rowBadges(r) {
  let out = '';
  for (const tag of (r.diet || [])) {
    const cls = tag === 'vegan' ? 'tag vegan' : 'tag';
    out += `<span class="${cls}">${escapeHtml(DIET_LABELS[tag] || tag)}</span>`;
  }
  if ((r.allergens || []).length) {
    out += `<span class="tag warn" title="${escapeHtml(r.allergens.join(', '))}">allergènes (${r.allergens.length})</span>`;
  }
  for (const flag of (r.flags || [])) {
    out += `<span class="tag warn">⚠ ${escapeHtml(FLAG_LABELS[flag] || flag)}</span>`;
  }
  if ((r.similar || []).length) {
    out += `<button type="button" class="tag dup" data-dup-id="${escapeHtml(r.id)}">🔁 doublon possible (${r.similar.length})</button>`;
  }
  return out;
}

function render() {
  const q = searchInput.value.trim();
  const dietFilter = filterDiet.value;
  const cuisineFilter = filterCuisine.value;
  const typeFilter = filterType.value;
  const warnOnly = toggleWarn.checked;
  const dupOnly = toggleDup.checked;
  const byLetter = {};
  let visible = 0;

  for (const r of DATA) {
    const title = currentTitle(r);
    const haystack = normalize(title + ' ' + r.title + ' ' + r.cuisine + ' ' + r.id + ' ' + r.dish_type);
    const matchesQ = !q || haystack.includes(normalize(q));
    const matchesDiet = !dietFilter || (r.diet || []).includes(dietFilter);
    const matchesCuisine = !cuisineFilter || r.cuisine === cuisineFilter;
    const matchesType = !typeFilter || r.dish_type === typeFilter;
    const matchesWarn = !warnOnly || (r.flags || []).length > 0;
    const matchesDup = !dupOnly || (r.similar || []).length > 0;
    if (!matchesQ || !matchesDiet || !matchesCuisine || !matchesType || !matchesWarn || !matchesDup) continue;
    visible++;
    const L = letterOf(title);
    (byLetter[L] = byLetter[L] || []).push(r);
  }

  visibleCountEl.textContent = visible;
  noResultsEl.classList.toggle('show', visible === 0);

  const headerH = document.querySelector('header.top').offsetHeight;

  let out = '';
  for (const L of ALPHABET) {
    if (!byLetter[L]) continue;
    out += `<section class="letter-group"><h2 class="letter-head" id="letter-${L === '#' ? 'hash' : L}" style="top:${headerH}px">${L}</h2><ul class="list">`;
    for (const r of byLetter[L]) {
      const title = currentTitle(r);
      const isMarked = marked.has(r.id);
      const isPending = pendingLink.has(r.id);
      const isComparePending = compareSet.has(r.id);
      const isRenamed = renamed.has(r.id);
      const memberOf = groupsForId(r.id);
      let checked = false;
      if (mode === 'del') checked = isMarked;
      else if (mode === 'link') checked = isPending;
      else checked = isComparePending;
      out += `<li class="row${isMarked ? ' marked' : ''}${isPending ? ' pending-link' : ''}${isComparePending ? ' pending-compare' : ''}" data-id="${r.id}">` +
        `<input type="checkbox" class="chk mode-${mode}" ${checked ? 'checked' : ''} aria-label="Sélectionner ${escapeHtml(title)}">` +
        `<div class="row-main">` +
        `<div class="row-title-line">` +
        `<span class="row-title">${highlight(title, q)}</span>` +
        `<button type="button" class="edit-btn" aria-label="Renommer" title="Renommer">` +
        `<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"></path></svg>` +
        `</button>` +
        `</div>` +
        `<div class="row-meta">` +
        (r.cuisine ? `<span class="tag">${escapeHtml(r.cuisine.replace(/_/g, ' '))}</span>` : '') +
        (r.dish_type ? `<span class="tag">${escapeHtml(r.dish_type)}</span>` : '') +
        rowBadges(r) +
        (isMarked ? `<span class="tag del">à supprimer</span>` : '') +
        (isRenamed ? `<span class="tag renamed">renommée</span>` : '') +
        (memberOf.length ? `<span class="tag link">groupe ${memberOf.join(', ')}</span>` : '') +
        `<span class="row-id">${escapeHtml(r.id)}</span>` +
        `</div></div></li>`;
    }
    out += '</ul></section>';
  }
  listRoot.innerHTML = out;
}

// ── Selection (delete / link / compare) ──────────────────────────────────
listRoot.addEventListener('click', (e) => {
  if (e.target.closest('.edit-btn')) return; // gere separement
  const dupBtn = e.target.closest('.tag.dup');
  if (dupBtn) {
    e.stopPropagation();
    openDuplicateCluster(dupBtn.dataset.dupId);
    return;
  }
  const row = e.target.closest('li.row');
  if (!row) return;
  const id = row.dataset.id;
  toggleSelection(id);
});

function toggleSelection(id) {
  if (mode === 'del') {
    marked.has(id) ? marked.delete(id) : marked.add(id);
  } else if (mode === 'link') {
    pendingLink.has(id) ? pendingLink.delete(id) : pendingLink.add(id);
  } else {
    if (compareSet.has(id)) {
      compareSet.delete(id);
    } else {
      if (compareSet.size >= MAX_COMPARE) {
        showToast(`Maximum ${MAX_COMPARE} recettes en comparaison à la fois.`);
        return;
      }
      compareSet.add(id);
    }
  }
  render();
  syncBars();
  syncLinkToolbar();
  syncCompareToolbar();
}

function syncLinkToolbar() {
  pendingLinkCountEl.textContent = pendingLink.size;
  saveGroupBtn.disabled = pendingLink.size < 1;
}
function syncCompareToolbar() {
  compareCountEl.textContent = compareSet.size;
  openCompareBtn.disabled = compareSet.size < 2;
}

modeDelBtn.addEventListener('click', () => setMode('del'));
modeLinkBtn.addEventListener('click', () => setMode('link'));
modeCompareBtn.addEventListener('click', () => setMode('compare'));
function setMode(m) {
  mode = m;
  modeDelBtn.classList.toggle('active', m === 'del');
  modeLinkBtn.classList.toggle('active', m === 'link');
  modeCompareBtn.classList.toggle('active', m === 'compare');
  linkToolbar.classList.toggle('show', m === 'link');
  compareToolbar.classList.toggle('show', m === 'compare');
  render();
}

function openDuplicateCluster(id) {
  const r = BY_ID[id];
  if (!r) return;
  compareSet.clear();
  compareSet.add(id);
  for (const s of (r.similar || [])) {
    if (compareSet.size >= MAX_COMPARE) break;
    compareSet.add(s.id);
  }
  setMode('compare');
  syncCompareToolbar();
  openCompareModal();
}

// ── Groupes ──────────────────────────────────────────────────────────────
saveGroupBtn.addEventListener('click', () => {
  if (pendingLink.size < 1) return;
  groups.push({ note: groupNoteInput.value.trim(), ids: Array.from(pendingLink) });
  pendingLink.clear();
  groupNoteInput.value = '';
  renderGroupsList();
  render();
  syncBars();
  syncLinkToolbar();
});
document.getElementById('clearPendingBtn').addEventListener('click', () => {
  pendingLink.clear();
  render();
  syncBars();
  syncLinkToolbar();
});
document.getElementById('clearCompareBtn').addEventListener('click', () => {
  compareSet.clear();
  render();
  syncCompareToolbar();
});
function renderGroupsList() {
  groupsListEl.innerHTML = groups.map((g, i) =>
    `<span class="group-chip">Groupe ${i + 1} — ${g.ids.length} recette(s)${g.note ? ' · ' + escapeHtml(g.note) : ''}` +
    `<button type="button" class="x" data-gi="${i}" aria-label="Supprimer ce groupe">×</button></span>`
  ).join('');
}
groupsListEl.addEventListener('click', (e) => {
  const btn = e.target.closest('.x');
  if (!btn) return;
  groups.splice(Number(btn.dataset.gi), 1);
  renderGroupsList();
  render();
  syncBars();
});

// ── Comparaison cote a cote ───────────────────────────────────────────────
const compareModal = document.getElementById('compareModal');
const compareRow = document.getElementById('compareRow');

function fmtIngredient(name) {
  return (name || '').replace(/_/g, ' ');
}

function compareCardHtml(r) {
  const diet = (r.diet || []).map(d => `<span class="tag ${d === 'vegan' ? 'vegan' : ''}">${escapeHtml(DIET_LABELS[d] || d)}</span>`).join('');
  const flags = (r.flags || []).map(f => `<span class="tag warn">⚠ ${escapeHtml(FLAG_LABELS[f] || f)}</span>`).join('');
  const compo = (r.composition || []).map(c =>
    `<tr><td>${escapeHtml(fmtIngredient(c.ingredient))}</td><td class="qty">${c.quantity != null ? c.quantity : ''} ${escapeHtml(c.unit || '')}</td></tr>`
  ).join('');
  return `<div class="compare-card" data-id="${escapeHtml(r.id)}">` +
    `<button type="button" class="compare-remove" data-remove-id="${escapeHtml(r.id)}">Retirer ✕</button>` +
    `<h3>${escapeHtml(currentTitle(r))}</h3>` +
    `<div class="compare-line">${escapeHtml((r.cuisine || '').replace(/_/g, ' ')) || '—'} · ${escapeHtml(r.dish_type || '—')}</div>` +
    `<div class="compare-line"><b>${r.servings ?? '?'}</b> pers. · <b>${r.time_total ?? '?'}</b> min · confiance <b>${r.confidence != null ? r.confidence.toFixed(2) : '?'}</b></div>` +
    `<div class="compare-chips">${diet}${flags}</div>` +
    (r.description ? `<p class="compare-desc">${escapeHtml(r.description)}</p>` : '') +
    (compo ? `<div class="compare-compo"><table>${compo}</table></div>` : '<div class="compare-compo">Composition vide.</div>') +
    `<span class="row-id">${escapeHtml(r.id)}</span>` +
    `</div>`;
}

function renderCompareModal() {
  const ids = Array.from(compareSet);
  compareRow.innerHTML = ids.map(id => BY_ID[id]).filter(Boolean).map(compareCardHtml).join('');
}
function openCompareModal() {
  renderCompareModal();
  compareModal.classList.add('show');
}
openCompareBtn.addEventListener('click', openCompareModal);
document.getElementById('compareModalClose').addEventListener('click', () => compareModal.classList.remove('show'));
compareModal.addEventListener('click', (e) => {
  if (e.target === compareModal) compareModal.classList.remove('show');
  const rm = e.target.closest('.compare-remove');
  if (rm) {
    compareSet.delete(rm.dataset.removeId);
    renderCompareModal();
    render();
    syncCompareToolbar();
  }
});
document.getElementById('copyCompareBtn').addEventListener('click', () => {
  const ids = Array.from(compareSet);
  const items = ids.map(id => BY_ID[id]).filter(Boolean);
  if (!items.length) { showToast('Rien à comparer.'); return; }
  const blocks = items.map(r => {
    const compoLines = (r.composition || []).map(c => `    - ${fmtIngredient(c.ingredient)} : ${c.quantity ?? ''} ${c.unit || ''}`).join('\\n');
    return `${currentTitle(r)} (${r.id})\\n` +
      `  cuisine=${r.cuisine || '?'} type=${r.dish_type || '?'} portions=${r.servings ?? '?'} temps=${r.time_total ?? '?'}min confiance=${r.confidence ?? '?'}\\n` +
      `  regime=${(r.diet || []).join(', ') || 'aucun'}\\n` +
      `  description: ${r.description || '(vide)'}\\n` +
      `  composition:\\n${compoLines || '    (vide)'}`;
  });
  copyTextRobust(`=== Comparaison (${items.length} recettes) ===\\n\\n` + blocks.join('\\n\\n'));
});

// ── Renommage inline ─────────────────────────────────────────────────────
listRoot.addEventListener('click', (e) => {
  const btn = e.target.closest('.edit-btn');
  if (!btn) return;
  e.stopPropagation();
  const row = btn.closest('li.row');
  const id = row.dataset.id;
  const r = BY_ID[id];
  const line = row.querySelector('.row-title-line');
  const titleSpan = row.querySelector('.row-title');
  const current = currentTitle(r);

  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'rename-input';
  input.value = current;
  line.replaceChild(input, titleSpan);
  btn.style.display = 'none';
  input.focus();
  input.select();

  function commit() {
    const val = input.value.trim();
    if (val && val !== r.title) {
      renamed.set(id, { oldTitle: r.title, newTitle: val });
    } else {
      renamed.delete(id);
    }
    render();
    syncBars();
  }
  input.addEventListener('blur', commit);
  input.addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter') { ev.preventDefault(); input.blur(); }
    if (ev.key === 'Escape') { input.value = current; input.blur(); }
  });
});

// ── Barre du bas + copie ─────────────────────────────────────────────────
function syncBars() {
  const parts = [];
  if (marked.size) parts.push(`<span class="del-n">${marked.size} <b>à supprimer</b></span>`);
  if (renamed.size) parts.push(`<span class="ren-n">${renamed.size} <b>renommée(s)</b></span>`);
  if (groups.length) parts.push(`<span class="link-n">${groups.length} <b>groupe(s)</b></span>`);
  bottombarCounts.innerHTML = parts.join('');
  bottombar.classList.toggle('show', marked.size > 0 || renamed.size > 0 || groups.length > 0);
  saveState(); // appelé apres chaque mutation (marked/groups/renamed) - sauvegarde continue
}

document.getElementById('clearAllBtn').addEventListener('click', () => {
  marked.clear();
  pendingLink.clear();
  groups.length = 0;
  renamed.clear();
  renderGroupsList();
  render();
  syncBars();
});

document.getElementById('copyBtn').addEventListener('click', async () => {
  const sections = [];

  if (marked.size) {
    const items = DATA.filter(r => marked.has(r.id));
    sections.push(`=== À supprimer (${items.length}) ===\\n` +
      items.map(r => `- ${r.id} | ${currentTitle(r)}`).join('\\n'));
  }
  if (renamed.size) {
    const lines = Array.from(renamed.entries()).map(([id, v]) =>
      `- ${id} | "${v.oldTitle}" → "${v.newTitle}"`);
    sections.push(`=== Renommages proposés (${renamed.size}) ===\\n` + lines.join('\\n'));
  }
  if (groups.length) {
    const blocks = groups.map((g, i) => {
      const items = g.ids.map(id => BY_ID[id]).filter(Boolean);
      const head = `Groupe ${i + 1}${g.note ? ' — ' + g.note : ''} (${items.length} recettes)`;
      const lines = items.map(r => `- ${r.id} | ${currentTitle(r)}`).join('\\n');
      return head + '\\n' + lines;
    });
    sections.push(`=== Groupes pour analyse (${groups.length}) ===\\n\\n` + blocks.join('\\n\\n'));
  }

  if (!sections.length) { showToast('Rien à copier pour l’instant.'); return; }
  const text = sections.join('\\n\\n');
  copyTextRobust(text);
});

// ── Copie robuste : API Clipboard -> execCommand -> modal manuel ──────────
const copyModal = document.getElementById('copyModal');
const copyModalText = document.getElementById('copyModalText');
const copyModalHint = document.getElementById('copyModalHint');

async function copyTextRobust(text) {
  // 1) API Clipboard moderne (peut être bloquée par le bac à sable de l'artifact)
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      showToast('Copié — colle le résultat dans le chat.');
      return;
    }
  } catch (e) { /* on tente le repli */ }

  // 2) document.execCommand (ancien mais fonctionne parfois quand l'API moderne est bloquée)
  if (tryExecCommandCopy(text)) {
    showToast('Copié — colle le résultat dans le chat.');
    return;
  }

  // 3) Repli manuel : zone de texte visible, pré-sélectionnée
  openCopyModal(text);
}

function tryExecCommandCopy(text) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.left = '-9999px';
  ta.style.top = '0';
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  let ok = false;
  try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
  document.body.removeChild(ta);
  return ok;
}

function openCopyModal(text) {
  copyModalText.value = text;
  copyModal.classList.add('show');
  copyModalText.focus();
  copyModalText.select();
}
document.getElementById('copyModalClose').addEventListener('click', () => {
  copyModal.classList.remove('show');
});
copyModal.addEventListener('click', (e) => {
  if (e.target === copyModal) copyModal.classList.remove('show');
});
document.getElementById('copyModalRetry').addEventListener('click', async () => {
  const text = copyModalText.value;
  copyModalText.focus();
  copyModalText.select();
  if (tryExecCommandCopy(text)) {
    showToast('Copié — colle le résultat dans le chat.');
    copyModal.classList.remove('show');
    return;
  }
  try {
    await navigator.clipboard.writeText(text);
    showToast('Copié — colle le résultat dans le chat.');
    copyModal.classList.remove('show');
  } catch (e) {
    copyModalHint.textContent = 'Toujours bloqué — sélectionnez le texte ci-dessus manuellement et faites Ctrl+C / Cmd+C.';
  }
});

function showToast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toastEl.classList.remove('show'), 2400);
}

let debounceT;
searchInput.addEventListener('input', () => {
  clearTimeout(debounceT);
  debounceT = setTimeout(render, 60);
});
filterDiet.addEventListener('change', render);
filterCuisine.addEventListener('change', render);
filterType.addEventListener('change', render);
toggleWarn.addEventListener('change', () => { toggleWarnLbl.classList.toggle('active-warn', toggleWarn.checked); render(); });
toggleDup.addEventListener('change', () => { toggleDupLbl.classList.toggle('active-dup', toggleDup.checked); render(); });

buildJumpNav();
renderStats();
const restored = loadState();
render();
renderGroupsList();
syncBars();
syncLinkToolbar();
syncCompareToolbar();
if (restored) showToast('Sélection précédente restaurée depuis ce navigateur.');
</script>
"""

html = html.replace("__DATA_JSON__", data_json).replace("__TOTAL__", str(len(data)))

out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
out_path.write_text(html, encoding="utf-8")
print(f"Ecrit -> {out_path} ({len(html)/1024:.0f} KB)")
