# Pipeline Reprise — Dashboard

Dashboard interactif de pilotage du sourcing pour une opération de reprise
d'entreprise. Visualise des cibles PME issues d'un sourcing automatisé
(axes industriels et prestations techniques) avec KPIs, filtres dynamiques
et liens directs vers les fiches d'entreprises.

## Démarrage rapide

### Utiliser l'app déployée
1. Ouvrir l'URL Streamlit Cloud (lien fourni séparément)
2. Glisser-déposer un CSV au format attendu dans la barre latérale
3. Filtrer, explorer, exporter

> 🔒 Les CSV importés restent en mémoire navigateur le temps de la session —
> aucune donnée n'est conservée côté serveur.

### Lancer en local
```bash
git clone https://github.com/ridchadata/pipeline-reprise-dashboard.git
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

## Protection par mot de passe (optionnel)

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
