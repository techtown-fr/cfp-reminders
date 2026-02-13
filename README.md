# CFP Reminders

Outil CLI pour suivre les dates limites des **Call for Papers** (CFP) des conférences tech, avec un focus sur la France.

## Pourquoi ?

Les deadlines des CFP passent vite. Cet outil agrège les CFP depuis [developers.events](https://developers.events), les filtre par pays, les trie par urgence et les affiche dans le terminal pour ne rien manquer.

## Quoi ?

- **Source de données** : [developers.events/all-cfps.json](https://developers.events/all-cfps.json)
- **Filtrage** : CFPs dont la localisation contient le pays demandé (ex. `(France)`)
- **Groupement par urgence** :
  - 🔴 **Cette semaine** (0–7 jours)
  - 🟡 **Ce mois-ci** (8–30 jours)
  - 🟢 **Plus tard** (31+ jours)
- **Cache local** : 1 heure de TTL pour limiter les appels API

## Comment ça marche ?

1. Récupération des données via l’API developers.events
2. Cache dans `~/.cache/cfp-reminders/cfps.json` (TTL 1 h)
3. Filtrage par pays et par date (seulement les deadlines futures)
4. Tri par date croissante
5. Affichage en table dans le terminal (Rich)

En cas d’erreur réseau, l’outil utilise le cache expiré si disponible (avec avertissement).

## Utilisation

### Prérequis

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommandé pour l’installation)

### Installation

```bash
# Avec uv (recommandé)
uv tool install .

# Ou en mode développement
uv sync
uv run cfp-reminders
```

### Commandes

```bash
# Afficher les CFPs en France (par défaut)
cfp-reminders

# Forcer le rafraîchissement (ignorer le cache)
cfp-reminders --refresh

# Filtrer par un autre pays
cfp-reminders --country "Germany"
cfp-reminders --country "Belgium"
```

### Options

| Option | Description | Défaut |
|--------|-------------|--------|
| `--country` | Pays à filtrer (ex. `France`, `Germany`) | `France` |
| `--refresh` | Ignorer le cache et récupérer les données à jour | `false` |

## Développement

```bash
# Installer les dépendances
uv sync --all-groups

# Lancer les tests (avec couverture)
uv run pytest --cov=cfp_reminders

# Linter et formatter (Ruff)
uv run ruff check . --fix
uv run ruff format .

# Hooks pre-commit (optionnel)
uv run pre-commit install
uv run pre-commit run --all-files
```
