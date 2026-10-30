# CFP Reminders

Outil CLI pour suivre les dates limites des **Call for Papers** (CFP) des conférences tech, avec un focus sur la France.

## Pourquoi ?

Les deadlines des CFP passent vite. Cet outil agrège les CFP depuis [developers.events](https://developers.events), les filtre par pays, les trie par urgence et les affiche dans le terminal pour ne rien manquer. Chaque lundi, il poste aussi un rappel dans l'espace Google Chat « Events » de TechTown.

## Quoi ?

- **Source de données** : [developers.events/all-cfps.json](https://developers.events/all-cfps.json)
- **Filtrage** : CFPs dont la localisation contient le pays demandé (ex. `(France)`)
- **Groupement par urgence** :
  - 🔴 **Cette semaine** (0 à 7 jours)
  - 🟡 **Ce mois-ci** (8 à 30 jours)
  - 🟢 **Plus tard** (31+ jours)
- **Cache local** : 1 heure de TTL pour limiter les appels API
- **Rappel Google Chat** : chaque lundi, les CFP qui ferment dans les 30 jours (voir plus bas)

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
| `--chat` | Poster un rappel dans Google Chat au lieu d'afficher les tables | `false` |
| `--webhook-url` | Webhook entrant Google Chat (ou variable `GOOGLE_CHAT_WEBHOOK_URL`) | aucun |
| `--days` | Fenêtre du rappel : CFP qui ferment dans N jours | `30` |
| `--dry-run` | Avec `--chat`, affiche le message sans le poster | `false` |

### Rappel hebdomadaire dans Google Chat

Le workflow `.github/workflows/cfp-reminder.yml` poste chaque lundi à 9 h 07 (heure de Paris) les CFP en France qui ferment dans les 30 jours. Si aucun CFP n'est concerné, rien n'est posté.

Mise en place :

1. Dans l'espace Google Chat, ouvrir *Applications et intégrations* > *Webhooks*, puis créer un webhook.
2. Enregistrer son URL dans le secret `GOOGLE_CHAT_WEBHOOK_URL` du dépôt.
3. Lancer le workflow à la main (*Run workflow*). Le dry-run est coché par défaut : le message s'affiche alors dans les logs sans être posté.

À savoir : sur un dépôt public, GitHub désactive un workflow planifié après 60 jours sans activité. Un commit ou une réactivation depuis l'onglet *Actions* le relance.

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
