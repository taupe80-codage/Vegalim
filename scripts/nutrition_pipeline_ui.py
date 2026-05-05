"""
Nutrition Pipeline Cockpit — v2
Corrections majeures + améliorations UX/design
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import os

# ─── CONFIG ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nutrition Pipeline Cockpit",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Syne:wght@400;600;700;800&display=swap');

/* ── Base ── */
[data-testid="stAppViewContainer"] { background: #0b0e14; }
[data-testid="stSidebar"]          { background: #0f1219 !important; border-right: 1px solid #1e2436; }
.stApp                             { font-family: 'Syne', sans-serif; color: #dce4f5; }
h1, h2, h3                         { font-family: 'Syne', sans-serif; font-weight: 800; }

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: #131825;
    border: 1px solid #1e2a42;
    border-radius: 10px;
    padding: 14px 18px;
}
[data-testid="stMetricValue"]  { font-family: 'JetBrains Mono', monospace; font-size: 2rem !important; }
[data-testid="stMetricLabel"]  { color: #5a6a8a; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; }

/* ── Expanders ── */
[data-testid="stExpander"] {
    background: #131825;
    border: 1px solid #1e2a42 !important;
    border-radius: 8px;
    margin-bottom: 6px;
}

/* ── Buttons ── */
.stButton > button {
    background: #1c2440;
    color: #7eb8f7;
    border: 1px solid #2a3a5e;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    padding: 4px 12px;
    transition: all 0.15s;
}
.stButton > button:hover {
    background: #223060;
    border-color: #4a7cc0;
    color: #a8d4ff;
}

/* ── Sidebar nav ── */
[data-testid="stRadio"] label {
    font-size: 13px;
    color: #8a9bb8;
    padding: 4px 0;
}
[data-testid="stRadio"] label:hover { color: #dce4f5; }

/* ── Info / success / error boxes ── */
.stSuccess { background: #0d2218 !important; border-left: 3px solid #00e676 !important; }
.stWarning { background: #1f1800 !important; border-left: 3px solid #ffab00 !important; }
.stError   { background: #200c0c !important; border-left: 3px solid #ff4444 !important; }
.stInfo    { background: #0c1a2e !important; border-left: 3px solid #4fc3f7 !important; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border: 1px solid #1e2a42; border-radius: 8px; }

/* ── Code / mono tags ── */
code { background: #1c2440; color: #7eb8f7; border-radius: 4px; padding: 1px 6px; font-size: 12px; }

/* ── Custom section title ── */
.section-title {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 20px;
    border-left: 3px solid #00e676;
    padding-left: 12px;
    margin: 20px 0 12px 0;
    color: #e8f0ff;
}

/* ── Status badges ── */
.badge-ok   { color: #00e676; font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 600; }
.badge-warn { color: #ffab00; font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 600; }
.badge-crit { color: #ff4444; font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 600; }

/* ── Score bar ── */
.score-bar-outer {
    background: #1c2440; border-radius: 4px; height: 8px; width: 100%; margin-top: 4px;
}
.score-bar-inner {
    height: 8px; border-radius: 4px; background: linear-gradient(90deg, #00e676, #00bcd4);
}

/* ── Hide streamlit branding ── */
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT FUNCTION — corrigée
# ═══════════════════════════════════════════════════════════════════════════════
def audit_nutrition(df: pd.DataFrame) -> pd.DataFrame:
    """
    Audit nutritionnel sur le DataFrame chargé.
    Corrections vs v1 :
    - water_g : gestion propre colonne manquante
    - atwater_bad : guard div/zero + seuil minimal calories
    - _audit_flags / _audit_explain : calcul row-by-row (plus de np.select sur f-strings)
    - score : seuil warning abaissé à >= 2 (cohérent avec validator_v11)
    - exempt : utilise .where() sur Series (fix numpy array)
    """
    o = df.copy()

    # Colonnes numériques obligatoires
    num_cols = ["calories_kcal", "protein_g", "carbs_g", "fat_g",
                "fiber_g", "sugar_g", "water_g"]
    for col in num_cols:
        if col not in o.columns:
            o[col] = 0.0
        o[col] = pd.to_numeric(o[col], errors="coerce").fillna(0.0)

    # Estimation Atwater
    est_kcal = 4 * o["protein_g"] + 4 * o["carbs_g"] + 9 * o["fat_g"]

    # Eau : colonne réelle ou estimée
    water_est = (100 - (o["protein_g"] + o["carbs_g"] + o["fat_g"] + o["fiber_g"])).clip(0, 100)
    water = o["water_g"].where(o["water_g"] > 0, water_est).clip(0, 100)

    dry = (100 - water).replace(0.0, np.nan)
    density = o["calories_kcal"] / dry

    # Règles
    fresh_dry_mix = (water > 70) & (density > 3.5)
    est_safe = est_kcal.where(est_kcal > 10, np.nan)  # évite div/0 sur ingrédients traces
    atwater_bad = (np.abs(o["calories_kcal"] - est_kcal) / est_safe > 0.30)
    fiber_gt = (o["fiber_g"] > o["carbs_g"]) & (o["carbs_g"] > 5)
    sugar_gt = (o["sugar_g"] > o["carbs_g"]) & (o["carbs_g"] > 5)

    score = (
        fresh_dry_mix.astype(int) * 3
        + atwater_bad.fillna(False).astype(int) * 2
        + fiber_gt.astype(int) * 2
        + sugar_gt.astype(int) * 1
    ).astype(int)

    # Exemptions catégories
    if "category" in o.columns:
        exempt = o["category"].isin({"nuts", "seeds", "dried_fruit", "spices", "herbs"})
        score = score.where(~exempt, 0)

    o["_audit_score"] = score
    o["_audit_severity"] = np.select(
        [score >= 5, score >= 2],
        ["🔴 Critical", "🟡 Warning"],
        default="✅ OK",
    )

    # Flags et explications — row-by-row pour éviter les bugs f-string Series
    all_flags, all_explains = [], []
    for i in o.index:
        flags, explains = [], []
        if fresh_dry_mix.loc[i]:
            flags.append("fresh_dry_mix")
            explains.append(
                f"Eau {water.loc[i]:.1f}% + densité {density.loc[i]:.2f} kcal/g·sec → mix frais/sec"
            )
        if atwater_bad.fillna(False).loc[i]:
            delta = abs(o.at[i, "calories_kcal"] - est_kcal.loc[i])
            pct = delta / max(est_kcal.loc[i], 1) * 100
            flags.append("atwater_mismatch")
            explains.append(
                f"Calories {o.at[i, 'calories_kcal']:.1f} vs estimé Atwater {est_kcal.loc[i]:.1f} (Δ{pct:.0f}%)"
            )
        if fiber_gt.loc[i]:
            flags.append("fiber_gt_carbs")
            explains.append(f"Fiber {o.at[i, 'fiber_g']}g > Carbs {o.at[i, 'carbs_g']}g")
        if sugar_gt.loc[i]:
            flags.append("sugar_gt_carbs")
            explains.append(f"Sugar {o.at[i, 'sugar_g']}g > Carbs {o.at[i, 'carbs_g']}g")
        all_flags.append(", ".join(flags) if flags else "—")
        all_explains.append(" | ".join(explains) if explains else "Aucune anomalie détectée")

    o["_audit_flags"] = all_flags
    o["_audit_explain"] = all_explains

    # Colonne nom normalisée
    # Priorité : _name déjà présent et non numérique > _ing_key > colonnes connues > index
    name_already_set = (
        "_name" in o.columns
        and not o["_name"].astype(str).str.match(r"^\d+$").all()
    )
    if not name_already_set:
        if "_ing_key" in o.columns:
            def _build_name(r):
                vk = str(r.get("_variant_key", "") or "")
                return r["_ing_key"] if vk in ("default", "") else f"{r['_ing_key']}[{vk}]"
            o["_name"] = o.apply(_build_name, axis=1)
        else:
            for possible in ["ingredient", "name", "label", "id"]:
                if possible in o.columns:
                    o["_name"] = o[possible].astype(str)
                    break
            else:
                o["_name"] = o.index.astype(str)

    return o


# ═══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT — parse la vraie structure imbriquée du pipeline
# Structure : {ingredients: {nom: {_meta: {category...}, variants: {vkey: {nutrients...}}}}}
# ═══════════════════════════════════════════════════════════════════════════════
SEARCH_PATHS = [
    "outputs/nutrition_patched_v7.json",
    "nutrition_patched_v7.json",
    "../outputs/nutrition_patched_v7.json",
    "backend/data/nutrition/reference/nutrition_corrected.json",
    "backend/data/nutrition/reference/nutrition_database_corrected.json",
]

NUTRIENT_COLS = [
    "calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g",
    "starch_g", "alcohol_g", "saturated_fat_g", "monounsaturated_fat_g",
    "polyunsaturated_fat_g", "omega3_g", "omega6_g", "cholesterol_mg",
    "sodium_mg", "calcium_mg", "iron_mg", "magnesium_mg", "phosphorus_mg",
    "potassium_mg", "zinc_mg", "copper_mg", "vitamin_c_mg", "vitamin_d_ug",
    "vitamin_b12_ug", "water_g",
]


@st.cache_data(show_spinner=False)
def flatten_nutrition_json(path: str) -> tuple:
    """
    Lit nutrition_patched_vX.json et aplatit la structure imbriquée en DataFrame.
    Retourne (df, raw_json).
    Structure source :
      root -> ingredients -> {ing_key} -> _meta + variants -> {variant_key} -> {nutrients}
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    ingredients = raw.get("ingredients", {})
    if not ingredients:
        if isinstance(raw, list):
            return pd.DataFrame(raw), raw
        return pd.DataFrame(), raw

    rows = []
    for ing_key, ing_data in ingredients.items():
        if not isinstance(ing_data, dict):
            continue
        meta     = ing_data.get("_meta", {})
        category = meta.get("category", "")
        name_fr  = meta.get("name_fr", ing_key)
        variants = ing_data.get("variants", {})
        if not variants:
            continue
        for variant_key, variant_data in variants.items():
            if not isinstance(variant_data, dict):
                continue
            row = {
                "_ing_key":     ing_key,
                "_variant_key": variant_key,
                "_name":        ing_key if variant_key == "default"
                                else f"{ing_key}[{variant_key}]",
                "category":     category,
                "name_fr":      name_fr,
            }
            for col in NUTRIENT_COLS:
                row[col] = variant_data.get(col, 0.0) or 0.0
            for extra in ["carbs_schema", "data_quality", "validation_score",
                          "source_key", "ingredient_type"]:
                row[extra] = variant_data.get(extra, "")
            rows.append(row)

    df = pd.DataFrame(rows)
    for col in NUTRIENT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df, raw


def try_load_auto() -> tuple:
    for path in SEARCH_PATHS:
        if os.path.exists(path):
            try:
                df, raw = flatten_nutrition_json(path)
                if not df.empty:
                    return df, path, raw
            except Exception:
                continue
    return pd.DataFrame(), "", {}


def build_variant_index(raw_json: dict) -> dict:
    """
    Construit un index { ing_key -> [ {variant_key, kcal, water, ingredient_type,
                                       data_quality, validation_score, sources, nutrients} ] }
    pour le picker de variants dans la page Anomalies.
    """
    idx: dict = {}
    ingredients = raw_json.get("ingredients", {})
    for ing_key, ing_data in ingredients.items():
        if not isinstance(ing_data, dict):
            continue
        variants = ing_data.get("variants", {})
        entries = []
        for vk, vd in variants.items():
            if not isinstance(vd, dict):
                continue
            prot  = float(vd.get("protein_g",  0) or 0)
            carbs = float(vd.get("carbs_g",    0) or 0)
            fat   = float(vd.get("fat_g",      0) or 0)
            fiber = float(vd.get("fiber_g",    0) or 0)
            water = float(vd.get("water_g",    0) or 0)
            kcal  = float(vd.get("calories_kcal", 0) or 0)
            water_est = max(0.0, 100.0 - (prot + carbs + fat + fiber))
            eff_water = water if water > 0 else water_est
            sources_raw = vd.get("sources", [])
            sources_list = (
                [s.get("name", "?") for s in sources_raw]
                if isinstance(sources_raw, list) else []
            )
            nutrient_snapshot = {c: float(vd.get(c, 0) or 0) for c in NUTRIENT_COLS}
            entries.append({
                "variant_key":      vk,
                "kcal":             round(kcal, 1),
                "water":            round(eff_water, 1),
                "water_real":       round(water, 1),
                "ingredient_type":  vd.get("ingredient_type", ""),
                "data_quality":     vd.get("data_quality", ""),
                "validation_score": vd.get("validation_score", None),
                "carbs_schema":     vd.get("carbs_schema", ""),
                "source_key":       vd.get("source_key", vk),
                "sources":          sources_list,
                "nutrients":        nutrient_snapshot,
            })
        if entries:
            idx[ing_key] = entries
    return idx


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ═══════════════════════════════════════════════════════════════════════════════
if "df" not in st.session_state:
    df_raw, found_path, raw_json = try_load_auto()
    if not df_raw.empty:
        st.session_state.df           = audit_nutrition(df_raw)
        st.session_state.source_path  = found_path
        st.session_state.raw_json     = raw_json
        st.session_state.variant_index = build_variant_index(raw_json)
    else:
        st.session_state.df           = pd.DataFrame()
        st.session_state.source_path  = ""
        st.session_state.raw_json     = {}
        st.session_state.variant_index = {}

if "history" not in st.session_state:
    st.session_state.history = []

if "alias_overrides" not in st.session_state:
    st.session_state.alias_overrides = {}

if "variant_index" not in st.session_state:
    st.session_state.variant_index = build_variant_index(
        st.session_state.get("raw_json", {})
    )

df = st.session_state.df


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='padding: 12px 0 20px 0;'>
        <div style='font-family: Syne, sans-serif; font-weight: 800; font-size: 18px; color: #e8f0ff;'>
            🔬 Nutrition Pipeline
        </div>
        <div style='font-family: JetBrains Mono, monospace; font-size: 10px; color: #3a4a6a; margin-top: 2px;'>
            COCKPIT v2
        </div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        ["📊 Dashboard",
         "🔄 Pipeline",
         "🚨 Anomalies",
         "🔗 Alias Manager",
         "📝 Historique"],
        label_visibility="collapsed",
    )

    st.divider()

    # ── Upload fallback ──
    if df.empty:
        st.markdown("**📂 Charger un fichier**")
        uploaded = st.file_uploader(
            "nutrition_patched_v7.json",
            type=["json"],
            label_visibility="collapsed",
        )
        if uploaded:
            try:
                raw_json = json.load(uploaded)
                # Sauver temporairement pour flatten_nutrition_json
                tmp_path = f"/tmp/{uploaded.name}"
                with open(tmp_path, "w", encoding="utf-8") as _f:
                    json.dump(raw_json, _f, ensure_ascii=False)
                df_raw, raw_json2 = flatten_nutrition_json(tmp_path)
                st.session_state.df = audit_nutrition(df_raw)
                st.session_state.source_path = uploaded.name
                st.session_state.raw_json = raw_json2
                st.session_state.variant_index = build_variant_index(raw_json2)
                df = st.session_state.df
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")
    else:
        src = st.session_state.get("source_path", "?")
        st.markdown(f"**Source :** `{os.path.basename(src)}`")
        n_ok = (df["_audit_severity"] == "✅ OK").sum()
        n_total = len(df)
        pct = n_ok / n_total * 100 if n_total else 0
        st.markdown(f"**Qualité :** {pct:.1f}%")
        st.markdown(f"""
        <div class='score-bar-outer'>
          <div class='score-bar-inner' style='width:{pct:.1f}%'></div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("💾 Export corrections", use_container_width=True):
            # Réinjecte les corrections manuelles dans le JSON source
            # puis sauvegarde un fichier de corrections séparé (ne remplace PAS v7)
            raw = st.session_state.get("raw_json", {})
            corr_log = []
            for idx, row in st.session_state.df.iterrows():
                ing_key     = row.get("_ing_key", "")
                variant_key = row.get("_variant_key", "default")
                if not ing_key or "ingredients" not in raw:
                    continue
                if ing_key not in raw["ingredients"]:
                    continue
                variants = raw["ingredients"][ing_key].get("variants", {})
                if variant_key not in variants:
                    continue
                for col in NUTRIENT_COLS:
                    if col in row.index:
                        old_val = variants[variant_key].get(col)
                        new_val = float(row[col])
                        if old_val is not None and abs(float(old_val) - new_val) > 0.001:
                            variants[variant_key][col] = new_val
                            corr_log.append(f"{ing_key}.{variant_key}.{col}: {old_val}→{new_val}")
            os.makedirs("outputs", exist_ok=True)
            with open("outputs/nutrition_patched_v7_corrected.json", "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2, ensure_ascii=False)
            st.success(f"✅ {len(corr_log)} corrections exportées → `outputs/nutrition_patched_v7_corrected.json`")
            st.session_state.history.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "action": "export_corrected",
                "item": "nutrition_patched_v7_corrected.json",
                "detail": f"{len(corr_log)} champs modifiés",
            })
    with col_b:
        if st.button("🔄 Re-audit", use_container_width=True) and not df.empty:
            clean = df[[c for c in df.columns if not c.startswith("_")]]
            st.session_state.df = audit_nutrition(clean)
            df = st.session_state.df
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE : DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.markdown("# 📊 Dashboard Général")

    if df.empty:
        st.warning("Aucune donnée chargée — utilisez l'upload dans la sidebar.")
        st.stop()

    n_total = len(df)
    n_crit  = (df["_audit_severity"] == "🔴 Critical").sum()
    n_warn  = (df["_audit_severity"] == "🟡 Warning").sum()
    n_ok    = (df["_audit_severity"] == "✅ OK").sum()
    score   = n_ok / n_total * 100 if n_total else 0

    # ── KPIs ──
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Ingrédients", n_total)
    c2.metric("✅ OK",       n_ok,   delta=None)
    c3.metric("🟡 Warning",  n_warn, delta=f"-{n_warn}" if n_warn else "0", delta_color="inverse")
    c4.metric("🔴 Critical", n_crit, delta=f"-{n_crit}" if n_crit else "0", delta_color="inverse")
    c5.metric("Data Quality", f"{score:.1f}%")

    st.markdown("---")

    # ── Charts ──
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("#### Répartition anomalies")
        sev_counts = df["_audit_severity"].value_counts().reset_index()
        sev_counts.columns = ["Sévérité", "Count"]
        color_map = {"✅ OK": "#00e676", "🟡 Warning": "#ffab00", "🔴 Critical": "#ff4444"}
        fig_pie = px.pie(
            sev_counts, names="Sévérité", values="Count",
            color="Sévérité", color_discrete_map=color_map,
            hole=0.55,
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#dce4f5", showlegend=True,
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            margin=dict(t=10, b=10, l=10, r=10),
        )
        fig_pie.update_traces(textfont_color="#dce4f5")
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        st.markdown("#### Flags les plus fréquents")
        flags_series = (
            df["_audit_flags"]
            .str.split(", ")
            .explode()
            .replace("—", pd.NA)
            .dropna()
        )
        if not flags_series.empty:
            flag_counts = flags_series.value_counts().reset_index()
            flag_counts.columns = ["Flag", "Occurrences"]
            fig_bar = px.bar(
                flag_counts, x="Occurrences", y="Flag", orientation="h",
                color_discrete_sequence=["#4fc3f7"],
            )
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#dce4f5", yaxis=dict(categoryorder="total ascending"),
                margin=dict(t=10, b=10, l=10, r=10), height=280,
            )
            fig_bar.update_xaxes(gridcolor="#1e2a42")
            fig_bar.update_yaxes(gridcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Aucun flag détecté.")

    # ── Distribution calories ──
    st.markdown("#### Distribution des calories (kcal/100g)")
    if "calories_kcal" in df.columns:
        fig_hist = px.histogram(
            df, x="calories_kcal", nbins=40,
            color_discrete_sequence=["#00bcd4"],
        )
        fig_hist.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#dce4f5", height=220,
            margin=dict(t=10, b=30, l=10, r=10),
            bargap=0.05,
        )
        fig_hist.update_xaxes(gridcolor="#1e2a42")
        fig_hist.update_yaxes(gridcolor="#1e2a42")
        st.plotly_chart(fig_hist, use_container_width=True)

    # ── Tableau rapide anomalies ──
    if n_crit + n_warn > 0:
        st.markdown("#### Anomalies à traiter")
        issues_df = df[df["_audit_severity"] != "✅ OK"][
            ["_name", "_audit_severity", "_audit_flags", "_audit_explain"]
        ].rename(columns={
            "_name": "Ingrédient",
            "_audit_severity": "Sévérité",
            "_audit_flags": "Flags",
            "_audit_explain": "Détail",
        })
        st.dataframe(issues_df, use_container_width=True, height=280)

    # ── No-match ontologie ──
    onto_data = st.session_state.get("onto_data", None)
    if onto_data:
        onto_keys = set(onto_data.get("ingredients", {}).keys())
        resolved_aliases = onto_data.get("aliases", {})  # {alias: real_key}
        all_resolved_targets = set(resolved_aliases.values())

        def _norm(s):
            import unicodedata
            s = s.lower()
            s = "".join(c for c in unicodedata.normalize("NFD", s)
                        if unicodedata.category(c) != "Mn")
            for ch in ["'", "'", " ", "-"]:
                s = s.replace(ch, "_")
            for ch in ["(", ")", ".", "%"]:
                s = s.replace(ch, "")
            while "__" in s:
                s = s.replace("__", "_")
            return s.strip("_")

        norm_onto = {_norm(k) for k in onto_keys}

        no_match = []
        for ing_key in df["_ing_key"].unique():
            in_onto  = ing_key in onto_keys
            in_alias = ing_key in resolved_aliases
            in_norm  = _norm(ing_key) in norm_onto
            if not in_onto and not in_alias and not in_norm:
                # Chercher candidats proches
                candidates = [k for k in onto_keys
                              if any(p in k for p in ing_key.split("_") if len(p) > 3)][:3]
                no_match.append({"Ingrédient": ing_key, "Candidats proches": ", ".join(candidates) or "—"})

        if no_match:
            st.markdown(f"#### 🔍 No-match ontologie — {len(no_match)} ingrédients sans correspondance")
            st.caption("Ces ingrédients n'ont pas de cible dans l'ontologie et ne bénéficieront pas de l'enrichissement multi-sources.")
            nm_df = pd.DataFrame(no_match)
            st.dataframe(nm_df, use_container_width=True, height=300)

    # ── Origine des données ──────────────────────────────────────────────────
    var_index = st.session_state.get("variant_index", {})
    if var_index:
        st.markdown("---")
        st.markdown("#### 🗂 Origine des données")
        st.caption("Vue agrégée des sources nutritionnelles par ingrédient et variant.")

        # Contrôles filtrage
        ori_col1, ori_col2, ori_col3 = st.columns([2, 2, 2])
        with ori_col1:
            ori_search = st.text_input("🔍 Filtrer ingrédient", "", key="ori_search")
        with ori_col2:
            all_sources = sorted({
                s for variants in var_index.values()
                for v in variants for s in v["sources"]
            })
            ori_source = st.selectbox("Source", ["Toutes"] + all_sources, key="ori_source")
        with ori_col3:
            all_qtypes = sorted({
                v["data_quality"] for variants in var_index.values()
                for v in variants if v["data_quality"]
            })
            ori_quality = st.selectbox("Qualité", ["Toutes"] + all_qtypes, key="ori_quality")

        DQ_ICON = {"exact": "🟢", "estimated": "🟡", "approximate": "🟠"}
        IT_ICON = {
            "raw": "🥦", "cooked": "🍳", "processed": "🏭",
            "refined": "⚗️", "fermented": "🫙", "additive": "🧪",
        }

        ori_rows = []
        for ing_key, variants in var_index.items():
            if ori_search and ori_search.lower() not in ing_key.lower():
                continue
            for v in variants:
                src_list = v["sources"]
                if ori_source != "Toutes" and ori_source not in src_list:
                    continue
                dq = v["data_quality"]
                if ori_quality != "Toutes" and dq != ori_quality:
                    continue
                vs = v["validation_score"]
                ori_rows.append({
                    "Ingrédient":  ing_key,
                    "Variant":     v["variant_key"],
                    "Type":        f"{IT_ICON.get(v['ingredient_type'], '•')} {v['ingredient_type']}",
                    "Sources":     " · ".join(src_list) if src_list else "—",
                    "Qualité":     f"{DQ_ICON.get(dq, '⚪')} {dq}" if dq else "—",
                    "Score valid.": f"{vs:.2f}" if vs is not None else "—",
                    "Carbs schema": v["carbs_schema"] or "—",
                    "Eau (%)":     v["water"],
                    "kcal":        v["kcal"],
                })

        if ori_rows:
            ori_df = pd.DataFrame(ori_rows)
            st.dataframe(ori_df, use_container_width=True, height=340, hide_index=True)
            st.caption(f"{len(ori_rows)} variant(s) affichés sur {sum(len(v) for v in var_index.values())} total")

            # KPIs sources
            from collections import Counter
            all_src_flat = [
                s for variants in var_index.values()
                for v in variants for s in v["sources"]
            ]
            src_counts = Counter(all_src_flat)
            total_variants = sum(len(v) for v in var_index.values())

            st.markdown("**Répartition des sources**")
            src_kpi_cols = st.columns(len(src_counts) or 1)
            for i, (src, cnt) in enumerate(src_counts.most_common()):
                pct = cnt / total_variants * 100
                src_kpi_cols[i % len(src_kpi_cols)].metric(src, f"{cnt}", f"{pct:.1f}% des variants")
        else:
            st.info("Aucun résultat avec ces filtres.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE : PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔄 Pipeline":
    st.markdown("# 🔄 Pipeline Complet")

    n_anomalies = (df["_audit_severity"] != "✅ OK").sum() if not df.empty else 0

    steps = [
        ("1", "Loading inputs",        "✅",  "292 ingrédients — `nutrition_database_corrected.json`"),
        ("2", "Tagging carbs_schema",  "✅",  "80 `available` · 342 `total`"),
        ("3", "Urgent hardcoded fixes","✅",  "41 fixes appliqués, 0 skippés"),
        ("4", "Selective proposals",   "✅",  "337 propositions acceptées · 2671 rejetées"),
        ("4b","Décontamination acaï",  "✅",  "0 variants affectés"),
        ("4c","Re-tagging carbs",      "✅",  "7 variants re-taggés"),
        ("5", "Post-validation fiber", "✅",  "0 warnings résiduels CIQUAL · 0 critical"),
        ("6", "Export outputs",        "✅",  "`nutrition_patched_v7.json` · `patch_report_v7.json`"),
        ("7", "Audit v2 (cockpit)",
              "🔴" if n_anomalies > 0 else "✅",
              f"{n_anomalies} anomalie(s) détectée(s) — voir onglet Anomalies"),
    ]

    for num, name, status, detail in steps:
        icon = "🔴" if status == "🔴" else ("🟡" if status == "🟡" else "✅")
        with st.expander(f"Étape {num} — {name}  {icon}", expanded=(status == "🔴")):
            st.markdown(detail, unsafe_allow_html=False)

    st.divider()

    # ── Lecture dynamique de l'ontologie ──
    onto_data = st.session_state.get("onto_data", None)
    if onto_data:
        resolved   = onto_data.get("aliases", {})
        missing_list = onto_data.get("aliases_missing", [])
        n_resolved = len(resolved)
        n_missing  = len(missing_list)

        if n_missing == 0:
            st.success(f"✅ Tous les alias sont résolus ({n_resolved} alias actifs dans l'ontologie).")
        else:
            st.warning(f"#### ⚠️ {n_missing} alias manquants — cibles introuvables dans l'ontologie")
            st.info("Rendez-vous dans l'onglet **🔗 Alias Manager** pour diagnostiquer.")
            cols = st.columns(4)
            for i, entry in enumerate(missing_list):
                with cols[i % 4]:
                    st.markdown(f"`{entry}`")

        st.markdown(f"#### ✅ {n_resolved} alias résolus")
        res_cols = st.columns(3)
        for i, (alias, target) in enumerate(resolved.items()):
            with res_cols[i % 3]:
                st.markdown(f"`{alias}` → `{target}`")
    else:
        st.info("Ontologie non chargée — lancez d'abord `build_ontology_v6.py` puis rechargez l'ontologie via le bouton ci-dessus.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE : ANOMALIES
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🚨 Anomalies":
    st.markdown("# 🚨 Anomalies & Corrections")

    if df.empty:
        st.error("Aucune donnée chargée.")
        st.stop()

    # ── Init état suggestions ──
    if "suggestions" not in st.session_state:
        st.session_state.suggestions = {}  # {idx: {field: new_val}}
    if "rejected" not in st.session_state:
        st.session_state.rejected = set()

    # ─────────────────────────────────────────────────────────────────────────
    # MOTEUR DE SUGGESTIONS — pré-calcule des corrections logiques par flag
    # ─────────────────────────────────────────────────────────────────────────
    # Valeurs fraîches connues (USDA) pour les ingrédients courants
    FRESH_KNOWN = {
        "ginger":      {"calories_kcal": 80.0,  "water_g": 78.0,  "protein_g": 1.8,  "carbs_g": 17.8, "fat_g": 0.75, "fiber_g": 2.0},
        "turmeric":    {"calories_kcal": 312.0, "water_g": 11.4,  "protein_g": 9.7,  "carbs_g": 67.1, "fat_g": 3.3,  "fiber_g": 22.7},
        "garlic":      {"calories_kcal": 149.0, "water_g": 58.6,  "protein_g": 6.4,  "carbs_g": 33.1, "fat_g": 0.5,  "fiber_g": 2.1},
        "celery":      {"calories_kcal": 14.0,  "water_g": 95.4,  "protein_g": 0.7,  "carbs_g": 3.0,  "fat_g": 0.2,  "fiber_g": 1.6},
        "capers":      {"calories_kcal": 23.0,  "water_g": 83.9,  "protein_g": 2.4,  "carbs_g": 4.9,  "fat_g": 0.9,  "fiber_g": 3.2},
        "asparagus":   {"calories_kcal": 20.0,  "water_g": 93.2,  "protein_g": 2.2,  "carbs_g": 3.9,  "fat_g": 0.1,  "fiber_g": 2.1},
        "sauerkraut":  {"calories_kcal": 19.0,  "water_g": 92.5,  "protein_g": 0.9,  "carbs_g": 4.3,  "fat_g": 0.1,  "fiber_g": 2.9},
        "mango":       {"calories_kcal": 60.0,  "water_g": 83.5,  "protein_g": 0.8,  "carbs_g": 15.0, "fat_g": 0.4,  "fiber_g": 1.6},
        "watermelon":  {"calories_kcal": 30.0,  "water_g": 91.4,  "protein_g": 0.6,  "carbs_g": 7.6,  "fat_g": 0.2,  "fiber_g": 0.4},
        "almond":      {"calories_kcal": 579.0, "water_g": 4.4,   "protein_g": 21.2, "carbs_g": 21.6, "fat_g": 49.9, "fiber_g": 12.5},
        "passion_fruit":{"calories_kcal": 97.0, "water_g": 72.9, "protein_g": 2.2,  "carbs_g": 23.4, "fat_g": 0.7,  "fiber_g": 10.4},
    }

    def compute_suggestions(row):
        """
        Retourne une liste de suggestions pour une ligne :
        [{"label": str, "field": str, "current": float, "suggested": float,
          "confidence": "high"|"medium"|"low", "source": str, "reason": str}]
        """
        suggestions = []
        flags = row.get("_audit_flags", "")
        name  = str(row.get("_ing_key", row.get("_name", ""))).lower()

        kcal  = float(row.get("calories_kcal", 0) or 0)
        prot  = float(row.get("protein_g", 0) or 0)
        carbs = float(row.get("carbs_g", 0) or 0)
        fat   = float(row.get("fat_g", 0) or 0)
        fiber = float(row.get("fiber_g", 0) or 0)
        sugar = float(row.get("sugar_g", 0) or 0)
        water = float(row.get("water_g", 0) or 0)

        atwater_est = round(4*prot + 4*carbs + 9*fat, 1)

        # ── atwater_mismatch ──────────────────────────────────────────────
        if "atwater_mismatch" in flags:
            # Suggestion 1 : recalcul Atwater pur
            if atwater_est > 5:
                delta_pct = abs(kcal - atwater_est) / max(atwater_est, 1) * 100
                conf = "high" if delta_pct < 50 else "medium"
                suggestions.append({
                    "label":     "Recalcul Atwater",
                    "field":     "calories_kcal",
                    "current":   kcal,
                    "suggested": atwater_est,
                    "confidence": conf,
                    "source":    "Calcul 4×prot + 4×carbs + 9×fat",
                    "reason":    f"Δ{delta_pct:.0f}% vs valeur actuelle",
                })
            # Suggestion 2 : valeur fraîche connue
            for known_name, known_vals in FRESH_KNOWN.items():
                if known_name in name or name in known_name:
                    known_kcal = known_vals["calories_kcal"]
                    suggestions.append({
                        "label":     f"Valeur fraîche USDA ({known_name})",
                        "field":     "calories_kcal",
                        "current":   kcal,
                        "suggested": known_kcal,
                        "confidence": "high",
                        "source":    "USDA FoodData Central",
                        "reason":    f"Ingrédient frais vs poudre/sec détecté",
                    })
                    # Proposer aussi water_g si très différent
                    if "water_g" in known_vals and abs(water - known_vals["water_g"]) > 20:
                        suggestions.append({
                            "label":     f"Teneur eau fraîche ({known_name})",
                            "field":     "water_g",
                            "current":   water,
                            "suggested": known_vals["water_g"],
                            "confidence": "high",
                            "source":    "USDA FoodData Central",
                            "reason":    "Cohérent avec la version fraîche",
                        })
                    break

        # ── fresh_dry_mix ─────────────────────────────────────────────────
        if "fresh_dry_mix" in flags and "atwater_mismatch" not in flags:
            # eau élevée + densité haute → probablement un mix frais/sec
            # Proposer de ramener les calories à Atwater
            if atwater_est > 5:
                suggestions.append({
                    "label":     "Aligner calories sur Atwater",
                    "field":     "calories_kcal",
                    "current":   kcal,
                    "suggested": atwater_est,
                    "confidence": "medium",
                    "source":    "Calcul Atwater",
                    "reason":    "Densité anormalement haute pour un aliment à haute teneur en eau",
                })

        # ── sugar_gt_carbs ────────────────────────────────────────────────
        if "sugar_gt_carbs" in flags:
            # sugar > carbs : probablement une erreur de source
            # Suggestion : plafonner sugar à carbs
            if carbs > 0:
                suggestions.append({
                    "label":     "Plafonner sugar à carbs",
                    "field":     "sugar_g",
                    "current":   sugar,
                    "suggested": round(carbs * 0.95, 2),
                    "confidence": "medium",
                    "source":    "Règle biochimique (sucres ⊆ glucides)",
                    "reason":    f"sugar {sugar}g > carbs {carbs}g : impossible",
                })
                # Ou carbs trop bas : proposer d'augmenter carbs
                carbs_est = round(sugar + max(0, fiber - sugar) + 1.0, 1)
                if carbs_est > carbs:
                    suggestions.append({
                        "label":     "Augmenter carbs_g pour couvrir sugar",
                        "field":     "carbs_g",
                        "current":   carbs,
                        "suggested": carbs_est,
                        "confidence": "low",
                        "source":    "Inférence (sugar + marge)",
                        "reason":    "Alternative : carbs sous-estimés",
                    })

        # ── fiber_gt_carbs ────────────────────────────────────────────────
        if "fiber_gt_carbs" in flags:
            # Souvent légitimement un schéma "available" vs "total"
            # Proposer d'augmenter carbs à fiber + sucres + marge
            carbs_total_est = round(fiber + sugar + 2.0, 1)
            suggestions.append({
                "label":     "Corriger carbs_g (schéma total)",
                "field":     "carbs_g",
                "current":   carbs,
                "suggested": carbs_total_est,
                "confidence": "medium",
                "source":    "Règle : carbs_total ≥ fiber + sugar",
                "reason":    f"fiber {fiber}g > carbs {carbs}g — schéma 'available' présumé",
            })

        return suggestions

    # ─────────────────────────────────────────────────────────────────────────
    # FILTRES
    # ─────────────────────────────────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 2])
    with fc1:
        sev_filter = st.multiselect(
            "Sévérité",
            ["🔴 Critical", "🟡 Warning", "✅ OK"],
            default=["🔴 Critical", "🟡 Warning"],
        )
    with fc2:
        flag_options = ["Tous"] + sorted(
            df["_audit_flags"].str.split(", ").explode()
            .replace("—", pd.NA).dropna().unique().tolist()
        )
        flag_filter = st.selectbox("Flag", flag_options)
    with fc3:
        cat_options = ["Toutes"] + sorted(df["category"].dropna().unique().tolist())
        cat_filter = st.selectbox("Catégorie", cat_options)
    with fc4:
        search = st.text_input("🔍 Ingrédient", "")

    # ─────────────────────────────────────────────────────────────────────────
    # FILTRAGE
    # ─────────────────────────────────────────────────────────────────────────
    issues = df[df["_audit_severity"].isin(sev_filter)].copy()
    if flag_filter != "Tous":
        issues = issues[issues["_audit_flags"].str.contains(flag_filter, na=False)]
    if cat_filter != "Toutes":
        issues = issues[issues["category"] == cat_filter]
    if search.strip():
        issues = issues[issues["_name"].str.contains(search.strip(), case=False, na=False)]

    # Exclure les rejets si on ne veut pas les voir
    show_rejected = st.checkbox("Afficher les anomalies rejetées", value=False)
    if not show_rejected:
        issues = issues[~issues.index.isin(st.session_state.rejected)]

    n_issues = len(issues)

    # ─────────────────────────────────────────────────────────────────────────
    # RÉSUMÉ TABULAIRE
    # ─────────────────────────────────────────────────────────────────────────
    if not issues.empty:
        summary_rows = []
        for idx, row in issues.iterrows():
            suggs = compute_suggestions(row)
            n_sugg = len(suggs)
            n_high = sum(1 for s in suggs if s["confidence"] == "high")
            ing_key = str(row.get("_ing_key", row.get("_name", "")) or "")
            name_fr = str(row.get("name_fr", "") or "")
            vk      = str(row.get("_variant_key", "") or "")
            display = f"{name_fr} ({ing_key})" if name_fr and name_fr != ing_key else ing_key
            if vk not in ("default", ""):
                display += f"  [{vk}]"
            # Origine
            var_index = st.session_state.get("variant_index", {})
            src_str, dq_str, itype_str = "—", "—", "—"
            if ing_key in var_index:
                for v in var_index[ing_key]:
                    if v["variant_key"] == (vk or "default"):
                        src_str   = ", ".join(v["sources"]) or "—"
                        dq_str    = v["data_quality"] or "—"
                        itype_str = v["ingredient_type"] or "—"
                        break
            summary_rows.append({
                "Sévérité":     row["_audit_severity"],
                "Ingrédient":   display,
                "Clé EN":       ing_key,
                "Catégorie":    row.get("category", ""),
                "Type":         itype_str,
                "Sources":      src_str,
                "Qualité":      dq_str,
                "Flags":        row["_audit_flags"],
                "kcal actuel":  round(row.get("calories_kcal", 0), 1),
                "carbs":        round(row.get("carbs_g", 0), 1),
                "sugar":        round(row.get("sugar_g", 0), 1),
                "fiber":        round(row.get("fiber_g", 0), 1),
                "💡 Suggestions": f"{n_high}✅ / {n_sugg} total",
            })
        summary_df = pd.DataFrame(summary_rows)
        st.markdown(f"**{n_issues} anomalie(s)** — vue résumée :")
        st.dataframe(summary_df, use_container_width=True, hide_index=True, height=220)
        st.divider()

    if n_issues == 0:
        st.success("✅ Aucune anomalie avec ces filtres.")
        st.stop()

    # ─────────────────────────────────────────────────────────────────────────
    # CARTES DÉTAILLÉES
    # ─────────────────────────────────────────────────────────────────────────
    CONF_COLOR = {"high": "#00e676", "medium": "#ffab00", "low": "#7eb8f7"}
    CONF_LABEL = {"high": "✅ Haute confiance", "medium": "🟡 Confiance moyenne", "low": "🔵 Basse confiance"}

    for idx, row in issues.iterrows():
        name     = row["_name"]
        category = row.get("category", "")
        severity = row["_audit_severity"]
        explain  = row["_audit_explain"]
        flags    = row["_audit_flags"]
        is_crit  = severity == "🔴 Critical"
        is_reject = idx in st.session_state.rejected

        reject_icon = "  ~~rejeté~~" if is_reject else ""
        name_fr  = str(row.get("name_fr", "") or "")
        ing_key  = str(row.get("_ing_key", name) or name)
        vk       = str(row.get("_variant_key", "") or "")
        # Libellé expander : nom FR + clé EN + catégorie
        display_name = f"{name_fr} ({ing_key})" if name_fr and name_fr != ing_key else ing_key
        variant_badge = f"  `{vk}`" if vk not in ("default", "") else ""
        label = f"{severity}  **{display_name}**{variant_badge}  `{category}`  —  `{flags}`{reject_icon}"

        with st.expander(label, expanded=(is_crit and not is_reject)):

            # ── En-tête ──
            h1, h2 = st.columns([3, 1])
            with h1:
                # Nom bien visible
                st.markdown(
                    f"<div style='font-family:Syne,sans-serif;font-size:18px;"
                    f"font-weight:800;color:#e8f0ff;margin-bottom:4px'>"
                    f"{display_name}{(' · <span style=\'color:#5a6a8a;font-size:14px\'>' + vk + '</span>') if vk not in ('default','') else ''}"
                    f"</div>"
                    f"<div style='font-family:JetBrains Mono,monospace;font-size:11px;"
                    f"color:#3a4a6a;margin-bottom:10px'>clé : {ing_key}</div>",
                    unsafe_allow_html=True,
                )
                for line in explain.split(" | "):
                    st.markdown(f"⚠️ {line}")
            with h2:
                st.markdown(f"**Catégorie :** `{category}`")
                st.markdown(f"**Variant :** `{vk or 'default'}`")
                if name_fr and name_fr != ing_key:
                    st.markdown(f"**FR :** {name_fr}")

            # ── Origine des données ──────────────────────────────────────────
            var_index = st.session_state.get("variant_index", {})
            current_variant_info = None
            if ing_key in var_index:
                for v in var_index[ing_key]:
                    if v["variant_key"] == (vk or "default"):
                        current_variant_info = v
                        break

            if current_variant_info:
                dq    = current_variant_info.get("data_quality", "")
                vscore = current_variant_info.get("validation_score")
                itype = current_variant_info.get("ingredient_type", "")
                cschema = current_variant_info.get("carbs_schema", "")
                src_list = current_variant_info.get("sources", [])

                dq_color = {
                    "exact":     "#00e676",
                    "estimated": "#ffab00",
                    "approximate": "#ff8c00",
                }.get(dq, "#5a6a8a")

                itype_color = {
                    "raw":        "#4fc3f7",
                    "cooked":     "#81c784",
                    "processed":  "#ffab00",
                    "refined":    "#ff8a65",
                    "fermented":  "#ce93d8",
                    "additive":   "#ef9a9a",
                }.get(itype, "#5a6a8a")

                vscore_str = f"{vscore:.2f}" if vscore is not None else "—"
                vscore_color = (
                    "#00e676" if vscore is not None and vscore >= 0.9
                    else "#ffab00" if vscore is not None and vscore >= 0.7
                    else "#ff4444"
                )

                src_badges = " ".join(
                    f"<code style='background:#1c2440;color:#7eb8f7;"
                    f"border-radius:4px;padding:1px 6px;font-size:11px'>{s}</code>"
                    for s in src_list
                ) if src_list else "<span style='color:#3a4a6a;font-size:11px'>aucune source</span>"

                st.markdown(
                    f"""
<div style='background:#0d1422;border:1px solid #1e2a42;border-radius:8px;
            padding:10px 14px;margin:8px 0 12px 0;display:flex;flex-wrap:wrap;gap:18px;
            align-items:center'>
  <div>
    <div style='font-size:10px;color:#3a4a6a;text-transform:uppercase;letter-spacing:1px'>Sources</div>
    <div style='margin-top:3px'>{src_badges}</div>
  </div>
  <div>
    <div style='font-size:10px;color:#3a4a6a;text-transform:uppercase;letter-spacing:1px'>Type</div>
    <div style='font-family:JetBrains Mono,monospace;font-size:12px;font-weight:600;
                color:{itype_color};margin-top:3px'>{itype or '—'}</div>
  </div>
  <div>
    <div style='font-size:10px;color:#3a4a6a;text-transform:uppercase;letter-spacing:1px'>Qualité</div>
    <div style='font-family:JetBrains Mono,monospace;font-size:12px;font-weight:600;
                color:{dq_color};margin-top:3px'>{dq or '—'}</div>
  </div>
  <div>
    <div style='font-size:10px;color:#3a4a6a;text-transform:uppercase;letter-spacing:1px'>Score valid.</div>
    <div style='font-family:JetBrains Mono,monospace;font-size:12px;font-weight:600;
                color:{vscore_color};margin-top:3px'>{vscore_str}</div>
  </div>
  <div>
    <div style='font-size:10px;color:#3a4a6a;text-transform:uppercase;letter-spacing:1px'>Carbs schema</div>
    <div style='font-family:JetBrains Mono,monospace;font-size:12px;font-weight:600;
                color:#dce4f5;margin-top:3px'>{cschema or '—'}</div>
  </div>
</div>
""",
                    unsafe_allow_html=True,
                )

            st.markdown("---")

            # ── Picker de variants (pour fresh_dry_mix) ────────────────────
            if "fresh_dry_mix" in flags and ing_key in var_index:
                other_variants = [
                    v for v in var_index[ing_key]
                    if v["variant_key"] != (vk or "default")
                ]
                if other_variants:
                    st.markdown(
                        "<div class='section-title' style='border-color:#ffab00'>"
                        "🔀 Matching douteux — choisir le bon variant"
                        "</div>",
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        "Ce variant mélange des valeurs incompatibles (humidité élevée + densité calorique sèche). "
                        "Sélectionne ci-dessous le variant correct à substituer."
                    )

                    # Construire le tableau comparatif
                    picker_rows = []
                    # Variant actuel en premier
                    cur_v = current_variant_info or {}
                    picker_rows.append({
                        "★ Variant":       f"**{vk or 'default'}** ← actuel",
                        "Type":            cur_v.get("ingredient_type", ""),
                        "Eau (%)":         cur_v.get("water", ""),
                        "kcal":            cur_v.get("kcal", ""),
                        "Qualité":         cur_v.get("data_quality", ""),
                        "Score":           f"{cur_v['validation_score']:.2f}" if cur_v.get("validation_score") is not None else "—",
                        "Sources":         ", ".join(cur_v.get("sources", [])),
                    })
                    for v in other_variants:
                        picker_rows.append({
                            "★ Variant":   v["variant_key"],
                            "Type":        v["ingredient_type"],
                            "Eau (%)":     v["water"],
                            "kcal":        v["kcal"],
                            "Qualité":     v["data_quality"],
                            "Score":       f"{v['validation_score']:.2f}" if v["validation_score"] is not None else "—",
                            "Sources":     ", ".join(v["sources"]),
                        })

                    st.dataframe(
                        pd.DataFrame(picker_rows),
                        use_container_width=True, hide_index=True,
                    )

                    # Sélecteur + bouton d'application
                    other_labels = [v["variant_key"] for v in other_variants]
                    chosen_vk = st.selectbox(
                        "Remplacer les nutriments par ceux du variant :",
                        other_labels,
                        key=f"vpick_{idx}",
                    )
                    chosen_info = next(
                        (v for v in other_variants if v["variant_key"] == chosen_vk), None
                    )
                    if chosen_info:
                        # Aperçu rapide
                        prev_cols = st.columns(4)
                        for ci, field in enumerate(["calories_kcal", "water_g", "protein_g", "fat_g"]):
                            cur_val = float(row.get(field, 0) or 0)
                            new_val = chosen_info["nutrients"].get(field, 0)
                            delta = new_val - cur_val
                            prev_cols[ci].metric(
                                field.replace("_g", "").replace("_kcal", " kcal").replace("_", " "),
                                f"{new_val:.1f}",
                                delta=f"{delta:+.1f}",
                                delta_color="normal",
                            )

                        if st.button(
                            f"✅ Substituer par le variant `{chosen_vk}`",
                            key=f"vswap_{idx}",
                            type="primary",
                        ):
                            applied = []
                            for field, new_val in chosen_info["nutrients"].items():
                                if field in st.session_state.df.columns:
                                    old_v = st.session_state.df.at[idx, field]
                                    st.session_state.df.at[idx, field] = new_val
                                    applied.append(f"{field}: {old_v:.2f}→{new_val:.2f}")
                            # Mettre à jour _variant_key dans le df
                            if "_variant_key" in st.session_state.df.columns:
                                st.session_state.df.at[idx, "_variant_key"] = chosen_vk
                            if "_name" in st.session_state.df.columns:
                                new_name = ing_key if chosen_vk == "default" else f"{ing_key}[{chosen_vk}]"
                                st.session_state.df.at[idx, "_name"] = new_name
                            st.session_state.history.append({
                                "time":   datetime.now().strftime("%H:%M:%S"),
                                "action": "variant_swap",
                                "item":   name,
                                "detail": f"Variant {vk or 'default'} → {chosen_vk} ({len(applied)} champs)",
                            })
                            st.success(
                                f"✅ Variant remplacé : `{vk or 'default'}` → `{chosen_vk}` "
                                f"({len(applied)} champs mis à jour)"
                            )
                            st.rerun()

                    st.markdown("---")

            # ── Tableau valeurs actuelles ──
            st.markdown("**Valeurs actuelles**")
            macro_cols = ["calories_kcal","protein_g","carbs_g","fat_g",
                          "fiber_g","sugar_g","water_g","sodium_mg","iron_mg"]
            vals = {}
            for c in macro_cols:
                if c in row.index:
                    vals[c.replace("_g","").replace("_kcal","").replace("_mg","")] = round(float(row[c] or 0), 2)
            st.dataframe(pd.DataFrame([vals]), use_container_width=True, hide_index=True)

            # ── Suggestions ──
            suggs = compute_suggestions(row)
            if suggs:
                st.markdown(f"**💡 {len(suggs)} suggestion(s) de correction**")

                for s_idx, sugg in enumerate(suggs):
                    conf  = sugg["confidence"]
                    color = CONF_COLOR[conf]
                    delta = sugg["suggested"] - sugg["current"]
                    delta_str = f"+{delta:.2f}" if delta > 0 else f"{delta:.2f}"

                    s1, s2, s3, s4, s5 = st.columns([3, 2, 2, 1, 1])
                    with s1:
                        st.markdown(
                            f"<span style='color:{color};font-family:JetBrains Mono,monospace;"
                            f"font-size:12px;font-weight:600'>{CONF_LABEL[conf]}</span>  "
                            f"**{sugg['label']}**",
                            unsafe_allow_html=True,
                        )
                        st.caption(f"📌 {sugg['reason']}  |  🗂 {sugg['source']}")
                    with s2:
                        st.markdown(f"Champ : `{sugg['field']}`")
                        st.markdown(f"Actuel : `{sugg['current']}`")
                    with s3:
                        st.markdown(f"Suggéré : **`{sugg['suggested']}`**")
                        st.markdown(f"Δ : `{delta_str}`")
                    with s4:
                        if st.button("✅ Accepter", key=f"acc_{idx}_{s_idx}"):
                            st.session_state.df.at[idx, sugg["field"]] = sugg["suggested"]
                            # Re-audit cette ligne
                            st.session_state.history.append({
                                "time":   datetime.now().strftime("%H:%M:%S"),
                                "action": f"accept_{sugg['label'].lower().replace(' ','_')}",
                                "item":   name,
                                "detail": f"{sugg['field']}: {sugg['current']} → {sugg['suggested']}",
                                "confidence": conf,
                            })
                            st.success(f"✅ {sugg['field']} = {sugg['suggested']}")
                            st.rerun()
                    with s5:
                        if st.button("❌ Rejeter", key=f"rej_{idx}_{s_idx}"):
                            st.session_state.history.append({
                                "time":   datetime.now().strftime("%H:%M:%S"),
                                "action": "reject_suggestion",
                                "item":   name,
                                "detail": f"{sugg['label']} ({sugg['field']}={sugg['suggested']})",
                            })
                            st.info("Suggestion rejetée — notée dans l'historique.")
            else:
                st.info("Aucune suggestion automatique pour ce flag. Utilisez l'édition manuelle.")

            st.markdown("---")

            # ── Actions manuelles ──
            st.markdown("**Actions manuelles**")
            btn1, btn2, btn3, btn4 = st.columns(4)

            # Recalcul Atwater
            with btn1:
                atwater_kcal = round(
                    4 * float(row.get("protein_g",0) or 0)
                    + 4 * float(row.get("carbs_g",0) or 0)
                    + 9 * float(row.get("fat_g",0) or 0), 1
                )
                if st.button(f"🔁 Atwater ({atwater_kcal} kcal)", key=f"atw_{idx}"):
                    st.session_state.df.at[idx, "calories_kcal"] = atwater_kcal
                    st.session_state.history.append({
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "action": "recalc_atwater",
                        "item": name,
                        "detail": f"calories_kcal → {atwater_kcal}",
                    })
                    st.success(f"calories_kcal = {atwater_kcal} kcal")
                    st.rerun()

            # Ignorer cette anomalie
            with btn2:
                if idx not in st.session_state.rejected:
                    if st.button("🚫 Ignorer", key=f"ignore_{idx}"):
                        st.session_state.rejected.add(idx)
                        st.session_state.history.append({
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "action": "ignore",
                            "item": name,
                            "detail": f"Anomalie ignorée ({flags})",
                        })
                        st.rerun()
                else:
                    if st.button("↩️ Restaurer", key=f"restore_{idx}"):
                        st.session_state.rejected.discard(idx)
                        st.rerun()

            # Édition manuelle champ libre
            with btn3:
                with st.popover("✏️ Édition libre"):
                    cols_edit = [c for c in NUTRIENT_COLS if c in row.index]
                    field = st.selectbox("Champ", cols_edit, key=f"field_{idx}")
                    new_val = st.number_input(
                        "Valeur", value=float(row.get(field, 0) or 0),
                        key=f"val_{idx}", format="%.4f"
                    )
                    if st.button("Appliquer", key=f"apply_{idx}"):
                        old_v = st.session_state.df.at[idx, field]
                        st.session_state.df.at[idx, field] = new_val
                        st.session_state.history.append({
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "action": "manual_edit",
                            "item": name,
                            "detail": f"{field}: {old_v} → {new_val}",
                        })
                        st.success(f"✅ {field} = {new_val}")
                        st.rerun()

            # Accepter toutes les suggestions haute confiance
            with btn4:
                high_suggs = [s for s in suggs if s["confidence"] == "high"]
                if high_suggs:
                    if st.button(f"⚡ Tout accepter ({len(high_suggs)} haute)", key=f"all_{idx}"):
                        for s in high_suggs:
                            st.session_state.df.at[idx, s["field"]] = s["suggested"]
                            st.session_state.history.append({
                                "time": datetime.now().strftime("%H:%M:%S"),
                                "action": "bulk_accept",
                                "item": name,
                                "detail": f"{s['field']}: {s['current']} → {s['suggested']}",
                                "confidence": "high",
                            })
                        st.success(f"✅ {len(high_suggs)} corrections appliquées")
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE : ALIAS MANAGER
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔗 Alias Manager":
    st.markdown("# 🔗 Alias Manager")

    # ── Chemins possibles vers ontology_v6.json ──
    ONTO_PATHS = [
        "backend/data/nutrition/reference/ontology_v6.json",
        "../backend/data/nutrition/reference/ontology_v6.json",
        "ontology_v6.json",
    ]

    @st.cache_data(show_spinner=False)
    def load_ontology(path: str) -> dict:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    # Trouver et charger l'ontologie
    onto = None
    onto_path_found = None
    for p in ONTO_PATHS:
        if os.path.exists(p):
            try:
                onto = load_ontology(p)
                onto_path_found = p
                break
            except Exception:
                continue

    if onto is None:
        st.error("❌ `ontology_v6.json` introuvable. Lancez d'abord `build_ontology_v6.py`.")
        st.info("Chemins cherchés :\n" + "\n".join(f"- `{p}`" for p in ONTO_PATHS))
        st.stop()

    # Stocker dans session pour la page Pipeline
    st.session_state["onto_data"] = onto

    onto_keys    = set(onto.get("ingredients", {}).keys())
    resolved_map = onto.get("aliases", {})          # {alias: cible_réelle}
    # aliases_missing n'est pas dans le JSON exporté — on le recalcule
    # depuis le rapport si dispo, sinon on infère depuis les clés
    report_path = onto_path_found.replace("ontology_v6.json", "ontology_v6_report.json")
    missing_raw = []
    if os.path.exists(report_path):
        try:
            with open(report_path, encoding="utf-8") as f:
                rpt = json.load(f)
            missing_raw = rpt.get("aliases_missing", [])
        except Exception:
            pass
    onto["aliases_missing"] = missing_raw

    st.markdown(f"**Source :** `{onto_path_found}`  |  **{len(onto_keys)} bases**  |  **{onto.get('total_bases', '?')} total**")
    st.markdown(f"Générée le `{onto.get('generated_at', '?')[:19]}`")

    st.divider()

    # ── KPIs alias ──
    n_resolved = len(resolved_map)
    n_missing  = len(missing_raw)
    ka, kb, kc = st.columns(3)
    ka.metric("✅ Alias résolus",   n_resolved)
    kb.metric("❌ Alias manquants", n_missing,
              delta=f"-{n_missing}" if n_missing else "0", delta_color="inverse")
    kc.metric("📦 Bases ontologie", len(onto_keys))

    st.divider()

    # ── Alias résolus ──
    if resolved_map:
        st.markdown("### ✅ Alias actifs")
        search_res = st.text_input("🔍 Filtrer", "", key="search_resolved")
        rows = [
            {"Alias (source)": alias, "→ Cible ontologie": target}
            for alias, target in sorted(resolved_map.items())
            if not search_res or search_res.lower() in alias.lower()
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=300)

    # ── Alias manquants ──
    st.divider()
    if n_missing == 0:
        st.success("🎉 Aucun alias manquant — toutes les cibles existent dans l'ontologie !")
    else:
        st.markdown(f"### ❌ {n_missing} alias manquants")
        st.warning(
            "Ces alias sont définis dans `ALIM_ALIASES` de `build_ontology_v6.py` "
            "mais leur cible est absente de l'ontologie. Corrigez `build_ontology_v6.py` "
            "puis relancez le build."
        )
        for entry in missing_raw:
            st.markdown(f"- `{entry}`")

    # ── No-match ingrédients ──
    st.divider()
    st.markdown("### 🔍 Recherche dans l'ontologie")
    st.caption("Vérifiez si un ingrédient ou une clé existe dans l'ontologie chargée.")
    query = st.text_input("Nom à chercher", "", key="onto_search")
    if query.strip():
        q = query.strip().lower()
        matches = [k for k in onto_keys if q in k.lower()]
        if matches:
            st.success(f"{len(matches)} résultat(s) :")
            for m in sorted(matches)[:30]:
                st.markdown(f"- `{m}`")
            if len(matches) > 30:
                st.caption(f"… et {len(matches)-30} autres")
        else:
            st.error(f"Aucune clé contenant `{query}` dans l'ontologie.")

    # ── Bouton reload ──
    st.divider()
    if st.button("🔄 Recharger l'ontologie depuis le disque"):
        st.cache_data.clear()
        st.session_state.pop("onto_data", None)
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE : HISTORIQUE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📝 Historique":
    st.markdown("# 📝 Historique des Corrections")

    if not st.session_state.history:
        st.info("Aucune correction enregistrée dans cette session.")
    else:
        hist_df = pd.DataFrame(st.session_state.history)
        st.dataframe(hist_df, use_container_width=True)

        if st.button("📤 Exporter historique JSON"):
            os.makedirs("outputs", exist_ok=True)
            with open("outputs/corrections_session.json", "w", encoding="utf-8") as f:
                json.dump(st.session_state.history, f, indent=2, ensure_ascii=False)
            st.success("✅ `outputs/corrections_session.json` exporté")

        if st.button("🗑️ Effacer historique"):
            st.session_state.history = []
            st.rerun()