# Pipeline Reprise — Dashboard

Dashboard interactif de pilotage du sourcing pour une opération de reprise
d'entreprise. Visualise des cibles PME issues d'un sourcing automatisé
(axes industriels et prestations techniques) avec KPIs, filtres dynamiques
et liens directs vers les fiches d'entreprises.

## Modes d'utilisation

Le dashboard supporte 4 sources de données, dans cet ordre de priorité :

1. **Upload manuel** — glisser-déposer d'un CSV dans la barre latérale.
   Prioritaire : remplace les autres sources pour la durée de la session.
2. **Google Sheets** (optionnel) — si `GOOGLE_SHEET_URL` ou `[google_sheets]`
   est défini dans les secrets Streamlit, le dashboard lit la feuille à chaque
   rafraîchissement (cache 5 min).
3. **Instantané embarqué** — les CSV `data/targets_*.csv` versionnés dans ce
   dépôt. C'est la source **par défaut et le filet de sécurité** : si les
   sources Google Sheets deviennent illisibles (feuille supprimée → `410 Gone`,
   partage révoqué → `403`), l'app bascule dessus automatiquement au lieu
   d'afficher une page vide.
4. **Local** — `data/` à côté de l'app, ou `../data/` si l'app vit dans un
   sous-dossier du projet de sourcing complet.

> ⚠️ Ce dépôt est **privé** : il embarque un instantané de données nominatives
> (dirigeants, âges, téléphones, emails). Il ne doit pas repasser en public, et
> le secret `DASHBOARD_PASSWORD` doit rester défini sur l'app déployée.

### Mettre à jour l'instantané embarqué
```bash
cp data/targets_<axe>_<date>.csv  <ce-dépôt>/data/
git add data/ && git commit -m "Données : instantané <date>" && git push
```
Streamlit Cloud redéploie seul en 1-2 min.

### Pour un destinataire non-technique
1. Cliquer sur l'URL fournie
2. (Si protection activée) Saisir le mot de passe
3. Le dashboard s'affiche immédiatement avec les données à jour

> 🔒 L'accès est protégé par mot de passe (secret `DASHBOARD_PASSWORD`).
> Les données servies proviennent de l'instantané embarqué dans ce dépôt privé,
> ou d'une Google Sheet si elle est configurée.

### Lancer en local
```bash
gh repo clone ridchadata/pipeline-reprise-dashboard   # dépôt privé
cd pipeline-reprise-dashboard
pip install -r requirements.txt
streamlit run dashboard.py
```

L'app s'ouvre sur http://localhost:8501.

## Format de CSV attendu

Colonnes minimales requises :
- `score` (0-10) — score de priorité de la cible
- `axe_detecte` — axe métier (ex: CND, METROLOGIE, MAINTENANCE)
- `denomination` — nom de l'entreprise
- `siren` — identifiant SIREN
- `naf` — code NAF (ex: "71.20B")
- `tranche_effectif` — code INSEE (11=10-19, 12=20-49, 21=50-99, 22=100-199, etc.)
- `categorie` — PME / ETI / GE
- `commune`, `departement` — localisation du siège
- `dirigeant_age_max` — âge maximum parmi les dirigeants identifiés
- `dirigeants` — détail texte des dirigeants

Colonnes optionnelles :
- `siege_dans_zone` — "oui"/"non"
- `url_pappers`, `url_societe` — liens directs (auto-générés depuis le SIREN sinon)
- `raison_sociale`, `etablissements_ouverts`, `date_creation`, etc.

Le CSV est typiquement généré par un script de sourcing dédié exploitant
les APIs publiques `recherche-entreprises.api.gouv.fr`, `data.gouv.fr`,
INSEE SIRENE et INPI RNE.

## Fonctionnalités

### KPIs
- Volume de cibles affichées vs total
- Tier 1 (score ≥ 5)
- Dirigeants 60+ ans (signal de transmission)
- Cibles axes prioritaires
- Couverture géographique

### Filtres dynamiques
- Axe métier (multi-select)
- Zone géographique (Vallée du Rhône, Normandie, Occitanie, IDF, etc.)
- Plage de score (slider)
- Âge dirigeant minimum (slider)
- Tranche d'effectif INSEE
- Catégorie d'entreprise (PME/ETI/GE)
- Recherche libre par nom ou SIREN

### Visualisations
- Distribution des scores avec coloration tier 1 / tier 2 / bas
- Cibles par zone géographique (bar chart horizontal)
- Pyramide des âges des dirigeants (signaux transmission)
- Répartition par axe métier (donut chart)

### Tableau exploitable
- Score affiché en barre de progression
- Liens directs cliquables vers Pappers et Société.com
- Tri sur n'importe quelle colonne
- Pagination configurable

### Export
- CSV de la sélection courante
- CSV tier 1 uniquement (cibles prioritaires)

## Configuration Google Sheets (mode partage)

Pour qu'un destinataire non-technique voie les données automatiquement
en cliquant sur l'URL :

### 1. Créer une Google Sheet
- Une feuille avec les colonnes attendues (voir plus haut)
- Pour mettre à jour : **File → Import → Upload → Replace current sheet**
  avec le CSV généré localement

### 2. Partager la sheet
- **Partage → Toute personne disposant du lien — Lecteur**
- Copier l'URL (format `https://docs.google.com/spreadsheets/d/.../edit#gid=0`)

### 3. Configurer dans Streamlit Cloud
**Settings → Secrets**, ajouter :

```toml
# Une seule sheet (le plus simple)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/TON_ID/edit#gid=0"

# Ou plusieurs sources (un onglet par axe)
[google_sheets]
"Pipeline complet" = "https://docs.google.com/spreadsheets/d/TON_ID/edit#gid=0"
"CND"              = "https://docs.google.com/spreadsheets/d/TON_ID/edit#gid=12345"
"Métrologie"       = "https://docs.google.com/spreadsheets/d/TON_ID/edit#gid=67890"
```

L'URL "/edit" classique est automatiquement convertie en URL d'export CSV
côté dashboard. Le cache se rafraîchit toutes les 5 minutes (bouton 🔄
dispo dans la sidebar pour forcer).

## Protection par mot de passe (recommandé en mode partage)

Pour restreindre l'accès à l'app déployée :

1. Dans Streamlit Cloud : **Settings → Secrets**
2. Ajouter :
   ```toml
   DASHBOARD_PASSWORD = "ton-mot-de-passe-fort"
   ```
3. Sauvegarder. L'app demande le mot de passe au premier accès.

Sans secret défini, l'app est ouverte (par défaut).

## Déploiement Streamlit Cloud

1. Fork ou push ce repo sur GitHub (public)
2. Aller sur https://share.streamlit.io
3. Connecter le compte GitHub
4. Cliquer **New app** → choisir le repo, branche `main`, fichier `dashboard.py`
5. **Deploy**

L'app est en ligne en 2-3 minutes.

## Stack technique

- **Streamlit** — framework UI Python
- **Plotly** — graphes interactifs
- **Pandas** — manipulation des données
- Aucune base de données côté serveur

## Licence

MIT.
