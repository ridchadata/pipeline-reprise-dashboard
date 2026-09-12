"""
Dashboard de pilotage du sourcing reprise d'entreprise.

Version cloud (Streamlit Community Cloud) : les données sont fournies
par l'utilisateur via un uploader de fichier — aucune donnée n'est
stockée côté serveur.

Mode local : si un dossier ../data/ existe avec des CSV, ils sont
auto-chargés (utile en exécution locale sur la machine de l'auteur).

Lancement local :
    streamlit run dashboard.py

Déploiement cloud :
    Push sur GitHub → connecter sur https://share.streamlit.io
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# Donnees locales : `data/` a cote de l'app (depot de deploiement autonome)
# ou `../data/` (app logee dans un sous-dossier du projet complet).
_HERE = Path(__file__).resolve().parent
DATA_DIR = _HERE / "data" if (_HERE / "data").is_dir() else _HERE.parent / "data"


# =========================================================================
# CONFIG STREAMLIT
# =========================================================================

st.set_page_config(
    page_title="Pipeline Reprise — Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 2rem; }
    [data-testid="stMetricLabel"] { font-size: 0.85rem; opacity: 0.8; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1 { padding-top: 0; }
    .stDataFrame { font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)


# =========================================================================
# PROTECTION PAR MOT DE PASSE (optionnel)
# =========================================================================
# Active une protection en définissant DASHBOARD_PASSWORD dans les
# secrets Streamlit Cloud (Settings > Secrets) :
#   DASHBOARD_PASSWORD = "ton-mot-de-passe"
# Si la variable est absente, l'app est ouverte à tous (par défaut).

def check_password() -> bool:
    expected = None
    try:
        expected = st.secrets.get("DASHBOARD_PASSWORD")
    except (FileNotFoundError, AttributeError):
        expected = os.environ.get("DASHBOARD_PASSWORD")

    if not expected:
        return True  # pas de protection configurée

    if st.session_state.get("auth_ok"):
        return True

    st.title("🔒 Accès protégé")
    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Entrer"):
        if pwd == expected:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect")
    return False


if not check_password():
    st.stop()


# =========================================================================
# LIBELLÉS HUMAINS
# =========================================================================

EFFECTIF_LIBELLES = {
    "00": "0 salarié", "01": "1-2", "02": "3-5", "03": "6-9",
    "11": "10-19", "12": "20-49", "21": "50-99", "22": "100-199",
    "31": "200-249", "32": "250-499", "41": "500-999",
    "NN": "non renseigné", "": "non renseigné",
}

ZONE_GEO_MAPPING = {
    # Vallée du Rhône
    "13": "Vallée du Rhône", "26": "Vallée du Rhône", "30": "Vallée du Rhône",
    "38": "Vallée du Rhône", "69": "Vallée du Rhône", "73": "Vallée du Rhône",
    "74": "Vallée du Rhône", "84": "Vallée du Rhône",
    # Normandie
    "14": "Normandie", "27": "Normandie", "50": "Normandie",
    "61": "Normandie", "76": "Normandie",
    # Occitanie
    "09": "Occitanie", "11": "Occitanie", "12": "Occitanie", "31": "Occitanie",
    "32": "Occitanie", "34": "Occitanie", "46": "Occitanie", "48": "Occitanie",
    "65": "Occitanie", "66": "Occitanie", "81": "Occitanie", "82": "Occitanie",
    # IDF
    "75": "Île-de-France", "77": "Île-de-France", "78": "Île-de-France",
    "91": "Île-de-France", "92": "Île-de-France", "93": "Île-de-France",
    "94": "Île-de-France", "95": "Île-de-France",
    # Hauts-de-France
    "02": "Hauts-de-France", "59": "Hauts-de-France", "60": "Hauts-de-France",
    "62": "Hauts-de-France", "80": "Hauts-de-France",
    # Grand Est
    "08": "Grand Est", "10": "Grand Est", "51": "Grand Est", "52": "Grand Est",
    "54": "Grand Est", "55": "Grand Est", "57": "Grand Est", "67": "Grand Est",
    "68": "Grand Est", "88": "Grand Est",
    # Pays de la Loire
    "44": "Pays de la Loire", "49": "Pays de la Loire", "53": "Pays de la Loire",
    "72": "Pays de la Loire", "85": "Pays de la Loire",
}


# =========================================================================
# CHARGEMENT DONNÉES
# =========================================================================

EXPECTED_COLUMNS = {
    "score", "axe_detecte", "denomination", "siren", "naf",
    "tranche_effectif", "categorie", "commune", "departement",
    "dirigeant_age_max", "dirigeants",
}


def normalize_df(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """Nettoie un dataframe brut et calcule les colonnes dérivées."""
    df = df.fillna("")
    # Numériques
    df["score"] = pd.to_numeric(df.get("score", 0), errors="coerce").fillna(0).astype(int)
    df["dirigeant_age_max"] = pd.to_numeric(df.get("dirigeant_age_max", None), errors="coerce")
    if "etablissements_ouverts" in df.columns:
        df["etablissements_ouverts"] = pd.to_numeric(
            df["etablissements_ouverts"], errors="coerce"
        ).fillna(0).astype(int)
    # Libellés humains
    df["effectif_libelle"] = df.get("tranche_effectif", "").astype(str).map(
        EFFECTIF_LIBELLES
    ).fillna("inconnu")
    df["zone_geo"] = df.get("departement", "").astype(str).map(ZONE_GEO_MAPPING).fillna("Autre")
    df["source_csv"] = source_name
    # Colonnes manquantes (si CSV partiel)
    for col in ("url_pappers", "url_societe", "siege_dans_zone", "raison_sociale"):
        if col not in df.columns:
            if col == "url_pappers":
                df[col] = df["siren"].apply(lambda s: f"https://www.pappers.fr/entreprise/{s}")
            elif col == "url_societe":
                df[col] = df["siren"].apply(lambda s: f"https://www.societe.com/societe/-{s}.html")
            else:
                df[col] = ""
    return df


@st.cache_data(ttl=60)
def list_local_csvs() -> list[Path]:
    if not DATA_DIR.exists():
        return []
    return sorted(DATA_DIR.glob("targets_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)


@st.cache_data(ttl=60)
def load_local_csv(path_str: str) -> pd.DataFrame:
    df = pd.read_csv(path_str, dtype=str)
    return normalize_df(df, Path(path_str).name)


def load_uploaded_csv(uploaded_file) -> pd.DataFrame:
    df = pd.read_csv(uploaded_file, dtype=str)
    return normalize_df(df, uploaded_file.name)


# =========================================================================
# CHARGEMENT DEPUIS GOOGLE SHEETS (mode "lien direct")
# =========================================================================
# Configurable via Streamlit secrets (Settings > Secrets sur share.streamlit.io)
# ou via variables d'environnement en local.
#
# Format secrets.toml :
#
#   # Une seule sheet :
#   GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/.../export?format=csv&gid=0"
#
#   # Plusieurs sheets (axes séparés par exemple) :
#   [google_sheets]
#   "Pipeline complet" = "https://docs.google.com/.../export?format=csv&gid=0"
#   "CND"              = "https://docs.google.com/.../export?format=csv&gid=12345"
#   "Métrologie"       = "https://docs.google.com/.../export?format=csv&gid=67890"
#
# La sheet doit être en partage "Toute personne disposant du lien — Lecteur".

def get_sheet_sources() -> dict[str, str]:
    """Retourne un dict {nom_lisible: url_export_csv} depuis secrets/env."""
    sources: dict[str, str] = {}

    # Format multi-sheets
    try:
        gs = st.secrets.get("google_sheets")
        if gs:
            for name, url in dict(gs).items():
                if url:
                    sources[str(name)] = str(url)
    except (FileNotFoundError, AttributeError):
        pass

    # Format URL unique (pratique pour démarrer)
    try:
        single = st.secrets.get("GOOGLE_SHEET_URL")
        if single:
            sources["Pipeline"] = str(single)
    except (FileNotFoundError, AttributeError):
        pass

    # Fallback variable d'environnement
    env_url = os.environ.get("GOOGLE_SHEET_URL")
    if env_url and "Pipeline" not in sources:
        sources["Pipeline"] = env_url

    return sources


def normalize_sheet_url(url: str) -> str:
    """Convertit une URL Google Sheets standard en URL d'export CSV.

    Accepte :
    - https://docs.google.com/spreadsheets/d/{ID}/edit#gid={GID}
    - https://docs.google.com/spreadsheets/d/{ID}/edit?gid={GID}
    - https://docs.google.com/spreadsheets/d/{ID}/export?format=csv&gid={GID}
    Tous sont normalisés en URL d'export CSV.
    """
    if "/export?" in url and "format=csv" in url:
        return url
    # Extraire l'ID
    import re
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not m:
        return url
    sheet_id = m.group(1)
    # Extraire le GID (onglet)
    g = re.search(r"[?#&]gid=(\d+)", url)
    gid = g.group(1) if g else "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def diagnose_sheet_error(exc: Exception) -> str:
    """Traduit une erreur de lecture Google Sheets en message actionnable."""
    from urllib.error import HTTPError

    if isinstance(exc, HTTPError):
        if exc.code == 410:
            return ("la feuille Google visée n'existe plus (supprimée, ou corbeille "
                    "vidée). Recrée une feuille et mets à jour `GOOGLE_SHEET_URL` "
                    "dans les secrets Streamlit.")
        if exc.code == 404:
            return ("feuille introuvable — l'identifiant du document ou le `gid` de "
                    "l'onglet est erroné dans les secrets.")
        if exc.code in (401, 403):
            return ("accès refusé — mets la feuille en partage « Toute personne "
                    "disposant du lien — Lecteur ».")
        return f"HTTP {exc.code} — {exc.reason}"
    return str(exc)


@st.cache_data(ttl=300)  # rafraîchit toutes les 5 minutes
def load_from_sheet(url: str, source_name: str) -> pd.DataFrame:
    """Charge un CSV depuis une URL Google Sheets publique."""
    csv_url = normalize_sheet_url(url)
    df = pd.read_csv(csv_url, dtype=str)
    return normalize_df(df, source_name)


def validate_columns(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """Vérifie que les colonnes essentielles sont présentes."""
    missing = EXPECTED_COLUMNS - set(df.columns)
    return len(missing) == 0, sorted(missing)


# =========================================================================
# UI — HEADER + SOURCES
# =========================================================================

st.title("🎯 Pipeline de reprise — tableau de bord")
st.caption("Sourcing automatisé via recherche-entreprises.api.gouv.fr · "
           "axes CND, Métrologie, Maintenance industrielle de niche")

local_csvs = list_local_csvs()
sheet_sources = get_sheet_sources()
local_options: dict[str, Path] = {}

with st.sidebar:
    st.header("📂 Sources de données")

    # Priorité d'affichage : Sheets > upload > local
    if sheet_sources:
        st.success(f"📊 {len(sheet_sources)} source(s) Google Sheets connectée(s)")
        sheet_choice = st.multiselect(
            "Sources actives",
            options=list(sheet_sources.keys()),
            default=list(sheet_sources.keys()),
        )
        col_r1, col_r2 = st.columns([1, 1])
        with col_r1:
            if st.button("🔄 Rafraîchir", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with col_r2:
            st.caption("auto: 5 min")
        st.divider()
        st.caption("Ou importer un CSV manuellement (override) :")
    else:
        sheet_choice = []

    uploaded_files = st.file_uploader(
        "Importer un CSV (optionnel)",
        type=["csv"],
        accept_multiple_files=True,
        help="Glisse-dépose un CSV pour visualiser une autre source. "
             "Si défini, remplace les sources Google Sheets pour la session.",
    )

    if local_csvs and not uploaded_files and not sheet_sources:
        st.divider()
        st.caption("📁 Mode local détecté")
        local_options = {f"{p.name}  ({p.stat().st_size // 1024} Ko)": p for p in local_csvs}
        selected_local = st.multiselect(
            "Fichiers locaux à charger",
            options=list(local_options.keys()),
            default=list(local_options.keys()),
        )
    else:
        selected_local = []


# ---- Chargement des données (priorité : upload > sheets > local) ----
dfs = []
errors = []
data_source_label = ""
fallback_used = False

if uploaded_files:
    data_source_label = f"{len(uploaded_files)} fichier(s) importé(s)"
    for uf in uploaded_files:
        try:
            df = load_uploaded_csv(uf)
            ok, missing = validate_columns(df)
            if not ok:
                errors.append(f"{uf.name} : colonnes manquantes : {missing}")
                continue
            dfs.append(df)
        except Exception as e:
            errors.append(f"{uf.name} : erreur de lecture : {e}")
elif sheet_choice:
    data_source_label = f"Google Sheets ({len(sheet_choice)} source(s))"
    for name in sheet_choice:
        try:
            df = load_from_sheet(sheet_sources[name], name)
            ok, missing = validate_columns(df)
            if not ok:
                errors.append(f"Sheet '{name}' : colonnes manquantes : {missing}")
                continue
            dfs.append(df)
        except Exception as e:
            errors.append(f"Source « {name} » : {diagnose_sheet_error(e)}")

    # Repli : si aucune source distante n'est lisible, on sert les données
    # embarquées dans le dépôt plutôt que d'afficher une page vide au visiteur.
    if not dfs and local_csvs:
        for path in local_csvs:
            try:
                dfs.append(load_local_csv(str(path)))
            except Exception as e:
                errors.append(f"{path.name} : erreur : {e}")
        if dfs:
            fallback_used = True
            data_source_label = f"{len(dfs)} fichier(s) embarqué(s) dans le dépôt"
elif selected_local:
    data_source_label = f"{len(selected_local)} fichier(s) local(aux)"
    for label in selected_local:
        path = local_options[label]
        try:
            df = load_local_csv(str(path))
            dfs.append(df)
        except Exception as e:
            errors.append(f"{path.name} : erreur : {e}")

if dfs:
    if fallback_used:
        st.info(
            "ℹ️ Les sources Google Sheets sont indisponibles : affichage des "
            "données embarquées dans le dépôt (dernier instantané publié)."
        )
    if errors:
        with st.expander("⚠️ Détail des avertissements de chargement", expanded=False):
            for err in errors:
                st.warning(err)

if not dfs:
    # Empty state — instructions
    if not sheet_sources:
        st.info(
            "👈 **Pour commencer** : importe un fichier CSV via la barre latérale, "
            "ou configure une source Google Sheets dans les secrets Streamlit."
        )
        st.markdown("""
        ### Configurer une source Google Sheets (recommandé pour partager)

        Dans **Streamlit Cloud → Settings → Secrets**, ajoute :

        ```toml
        # Une seule sheet
        GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/TON_ID/edit#gid=0"

        # Ou plusieurs (un onglet par axe par exemple)
        [google_sheets]
        "Pipeline complet" = "https://docs.google.com/spreadsheets/d/TON_ID/edit#gid=0"
        "CND"              = "https://docs.google.com/spreadsheets/d/TON_ID/edit#gid=12345"
        "Métrologie"       = "https://docs.google.com/spreadsheets/d/TON_ID/edit#gid=67890"
        ```

        La sheet doit être en partage **"Toute personne disposant du lien — Lecteur"**.

        ### Sinon : importer un CSV manuellement
        Glisse-dépose un fichier généré par le script de sourcing dans la zone "Importer un CSV"
        de la barre latérale.

        ### Fonctionnalités du dashboard
        - 📊 KPIs synthétiques (volume, tier 1, signaux transmission)
        - 📈 Graphes interactifs (scores, géographies, âges, axes)
        - 🎯 Tableau filtrable avec liens directs Pappers et Société.com
        - ⬇️ Export du sous-ensemble filtré
        """)
    else:
        st.error("Aucune donnée à afficher — la ou les sources configurées sont illisibles.")
        for err in errors:
            st.warning(err)
        st.markdown("""
        ### Rétablir la source de données

        1. **Recréer la feuille** sur https://sheets.google.com et y importer le
           dernier CSV du pipeline (`Fichier → Importer → Remplacer la feuille`).
        2. **Partager** : `Partager → Accès général → Toute personne disposant du
           lien → Lecteur`.
        3. **Mettre à jour le secret** dans *Streamlit Cloud → Settings → Secrets* :

           ```toml
           GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/NOUVEL_ID/edit#gid=0"
           ```

        *Alternative sans Google Sheets* : déposer un CSV `targets_*.csv` dans le
        dossier `data/` du dépôt — l'app le sert automatiquement en repli.
        """)
    st.stop()


# Concaténation + dédoublonnage par siren
df_raw = pd.concat(dfs, ignore_index=True)
df_raw = df_raw.sort_values("score", ascending=False).drop_duplicates(subset=["siren"], keep="first")

# Indicateur de source (au-dessus des KPIs)
st.caption(f"📡 Source : **{data_source_label}** · {len(df_raw):,} cibles uniques après dédoublonnage SIREN".replace(",", " "))


# =========================================================================
# FILTRES (sidebar suite)
# =========================================================================

with st.sidebar:
    st.divider()
    st.header("🎛️ Filtres")

    axes_dispo = sorted(df_raw["axe_detecte"].unique())
    axes_filter = st.multiselect("Axe métier", axes_dispo, default=axes_dispo)

    zones_dispo = sorted([z for z in df_raw["zone_geo"].unique() if z])
    zones_filter = st.multiselect("Zone géographique", zones_dispo, default=zones_dispo)

    score_min, score_max = st.slider(
        "Plage de score",
        min_value=0, max_value=10,
        value=(3, 10),
        help="Score 5+ = tier 1 prioritaire",
    )

    age_min = st.slider(
        "Âge dirigeant minimum",
        min_value=0, max_value=85, value=0,
        help="55+ = signal transmission · 60+ = priorité forte",
    )

    eff_dispo = sorted([e for e in df_raw["tranche_effectif"].unique() if e])
    eff_options = [f"{e} ({EFFECTIF_LIBELLES.get(e, '?')})" for e in eff_dispo]
    eff_default = [o for o in eff_options if o.startswith(("11 ", "12 ", "21 ", "22 "))]
    eff_choice = st.multiselect(
        "Tranche effectif",
        eff_options,
        default=eff_default if eff_default else eff_options,
    )
    eff_codes_selected = [c.split(" ")[0] for c in eff_choice]

    cat_dispo = sorted([c for c in df_raw["categorie"].unique() if c])
    cat_filter = st.multiselect("Catégorie INSEE", cat_dispo, default=cat_dispo) if cat_dispo else []

    if "siege_dans_zone" in df_raw.columns:
        siege_options = sorted([s for s in df_raw["siege_dans_zone"].unique() if s])
        siege_filter = st.multiselect(
            "Siège dans zone ciblée", siege_options, default=siege_options
        )
    else:
        siege_filter = []

    search = st.text_input("Recherche par nom ou SIREN", placeholder="Tape pour filtrer")


# ---- Application des filtres ----
df = df_raw.copy()
df = df[df["axe_detecte"].isin(axes_filter)]
df = df[df["zone_geo"].isin(zones_filter)]
df = df[(df["score"] >= score_min) & (df["score"] <= score_max)]
if age_min > 0:
    df = df[df["dirigeant_age_max"].fillna(0) >= age_min]
if eff_codes_selected:
    df = df[df["tranche_effectif"].isin(eff_codes_selected)]
if cat_filter:
    df = df[df["categorie"].isin(cat_filter)]
if siege_filter and "siege_dans_zone" in df.columns:
    df = df[df["siege_dans_zone"].isin(siege_filter)]
if search:
    s = search.lower()
    df = df[
        df["denomination"].str.lower().str.contains(s, na=False)
        | df["siren"].astype(str).str.contains(s, na=False)
    ]


# =========================================================================
# KPIs
# =========================================================================

n_total = len(df_raw)
n_filtered = len(df)
n_tier1 = (df["score"] >= 5).sum()
n_dirigeants_60 = (df["dirigeant_age_max"] >= 60).sum()
n_metrologie = (df["axe_detecte"] == "METROLOGIE").sum()
n_cnd = df["axe_detecte"].str.startswith("CND", na=False).sum()
n_zones = df["zone_geo"].nunique()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(
    "Cibles affichées", f"{n_filtered:,}".replace(",", " "),
    delta=f"sur {n_total:,} au total".replace(",", " ") if n_filtered != n_total else None,
)
c2.metric(
    "Tier 1 (score ≥5)", f"{n_tier1:,}".replace(",", " "),
    delta=f"{(n_tier1 / max(n_filtered, 1) * 100):.0f}% des affichées",
    delta_color="off",
)
c3.metric(
    "Dirigeants 60+ ans", f"{n_dirigeants_60:,}".replace(",", " "),
    delta=f"{(n_dirigeants_60 / max(n_filtered, 1) * 100):.0f}% des affichées",
    delta_color="off",
)
c4.metric("Cibles CND + Métrologie", f"{n_cnd + n_metrologie:,}".replace(",", " "))
c5.metric("Zones couvertes", f"{n_zones}", delta_color="off")

st.divider()


# =========================================================================
# GRAPHES
# =========================================================================

g1, g2 = st.columns([1, 1])

with g1:
    st.subheader("Distribution des scores")
    score_counts = df["score"].value_counts().sort_index()
    score_df = pd.DataFrame({"Score": score_counts.index, "Cibles": score_counts.values})
    score_df["Tier"] = score_df["Score"].apply(
        lambda s: "Tier 1 (≥5)" if s >= 5 else ("Tier 2 (3-4)" if s >= 3 else "Bas (0-2)")
    )
    fig = px.bar(
        score_df, x="Score", y="Cibles", color="Tier",
        color_discrete_map={
            "Tier 1 (≥5)": "#22c55e",
            "Tier 2 (3-4)": "#3b82f6",
            "Bas (0-2)": "#94a3b8",
        },
        text="Cibles",
    )
    fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(tickmode="linear"), showlegend=True)
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

with g2:
    st.subheader("Cibles par zone géographique")
    zone_counts = df["zone_geo"].value_counts().reset_index()
    zone_counts.columns = ["Zone", "Cibles"]
    fig = px.bar(
        zone_counts, x="Cibles", y="Zone",
        orientation="h", text="Cibles", color="Cibles",
        color_continuous_scale="Tealgrn",
    )
    fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10),
                      yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)


g3, g4 = st.columns([1, 1])

with g3:
    st.subheader("Pyramide des âges des dirigeants")
    df_age = df[df["dirigeant_age_max"].notna() & (df["dirigeant_age_max"] > 0)].copy()
    if not df_age.empty:
        bins = [0, 40, 50, 55, 60, 65, 70, 100]
        labels = ["<40", "40-49", "50-54", "55-59", "60-64", "65-69", "70+"]
        df_age["tranche"] = pd.cut(df_age["dirigeant_age_max"], bins=bins, labels=labels, right=False)
        age_counts = df_age["tranche"].value_counts().reindex(labels).fillna(0).astype(int).reset_index()
        age_counts.columns = ["Tranche", "Cibles"]
        age_counts["Signal"] = age_counts["Tranche"].apply(
            lambda t: "Signal fort (60+)" if t in ("60-64", "65-69", "70+")
            else ("Signal modéré (55-59)" if t == "55-59" else "Hors signal")
        )
        fig = px.bar(
            age_counts, x="Tranche", y="Cibles", color="Signal", text="Cibles",
            color_discrete_map={
                "Signal fort (60+)": "#22c55e",
                "Signal modéré (55-59)": "#f59e0b",
                "Hors signal": "#94a3b8",
            },
        )
        fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas de données d'âge disponibles dans la sélection.")

with g4:
    st.subheader("Répartition par axe métier")
    axe_counts = df["axe_detecte"].value_counts().reset_index()
    axe_counts.columns = ["Axe", "Cibles"]
    fig = px.pie(
        axe_counts, names="Axe", values="Cibles", hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
    fig.update_traces(textinfo="label+percent+value", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)


# =========================================================================
# TOP CIBLES
# =========================================================================

st.divider()
st.subheader("🏆 Top cibles à traiter en priorité")

display_cols = [
    "score", "axe_detecte", "denomination", "categorie",
    "effectif_libelle", "commune", "departement", "zone_geo",
    "dirigeant_age_max", "dirigeants",
    "url_pappers", "url_societe",
    "siren", "naf",
]
available_cols = [c for c in display_cols if c in df.columns]
df_display = df[available_cols].rename(columns={
    "score": "Score", "axe_detecte": "Axe", "denomination": "Entreprise",
    "categorie": "Catégorie", "effectif_libelle": "Effectif",
    "commune": "Commune", "departement": "Dept", "zone_geo": "Zone",
    "dirigeant_age_max": "Âge max dir.",
    "dirigeants": "Dirigeants (détail)",
    "url_pappers": "Pappers", "url_societe": "Societe.com",
    "siren": "SIREN", "naf": "NAF",
}).sort_values("Score", ascending=False)

n_show = st.slider("Nombre de cibles à afficher", 10, 200, 30, step=10)

st.dataframe(
    df_display.head(n_show),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Score": st.column_config.ProgressColumn(
            "Score", min_value=0, max_value=10, format="%d/10",
        ),
        "Pappers": st.column_config.LinkColumn("Pappers", display_text="🔗 Voir"),
        "Societe.com": st.column_config.LinkColumn("Société.com", display_text="🔗 Voir"),
        "Âge max dir.": st.column_config.NumberColumn("Âge max dir.", format="%d ans"),
        "Dirigeants (détail)": st.column_config.TextColumn(
            "Dirigeants (détail)", width="large",
        ),
    },
    height=600,
)


# =========================================================================
# EXPORT
# =========================================================================

st.divider()
exp1, exp2, exp3 = st.columns([1, 1, 2])

with exp1:
    csv_buffer = io.StringIO()
    df_display.to_csv(csv_buffer, index=False)
    st.download_button(
        label=f"⬇️ Télécharger la sélection ({len(df)} lignes)",
        data=csv_buffer.getvalue(),
        file_name=f"cibles_filtrees_{n_filtered}.csv",
        mime="text/csv",
    )

with exp2:
    df_tier1 = df_display[df_display["Score"] >= 5]
    csv_t1 = df_tier1.to_csv(index=False)
    st.download_button(
        label=f"⬇️ Tier 1 uniquement ({len(df_tier1)} cibles)",
        data=csv_t1,
        file_name="cibles_tier1.csv",
        mime="text/csv",
        type="primary",
    )

with exp3:
    st.caption(
        "💡 *Le tier 1 (score ≥ 5) regroupe les cibles avec un fit fort sur "
        "axe + effectif + signal transmission. À traiter en priorité.*"
    )

st.caption(
    f"🔒 Aucune donnée n'est conservée côté serveur — les fichiers importés "
    f"restent en mémoire le temps de la session."
)
