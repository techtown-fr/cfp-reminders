# CFP Reminders : contexte pour Claude

## Vue d'ensemble

CLI Python pour suivre les deadlines des **Call for Papers** (CFP) des conférences tech. Source : [developers.events](https://developers.events/all-cfps.json). Focus France par défaut.

Un workflow planifié poste aussi chaque lundi un rappel dans l'espace Google Chat « Events » de TechTown. Dépôt public : `techtown-fr/cfp-reminders`.

## Stack technique

- **Python 3.12+** : `from __future__ import annotations` partout
- **uv** : gestion des dépendances et exécution
- **click** : CLI
- **httpx** : requêtes HTTP
- **rich** : affichage terminal (tables, couleurs)
- **pytest** + **pytest-httpx** + **pytest-cov** : tests et couverture
- **Ruff** : linter et formatter
- **pre-commit** : hooks Git (Ruff, trailing-whitespace, etc.)

## Structure du projet

```text
cfp-reminders/
├── pyproject.toml          # uv, hatchling, Ruff, entry point cfp-reminders
├── .gitignore
├── .pre-commit-config.yaml
├── .github/
│   ├── workflows/ci.yml   # Lint (Ruff) + tests (pytest-cov)
│   ├── workflows/cfp-reminder.yml  # Rappel Google Chat, lundi 9 h 07 Europe/Paris
│   └── dependabot.yml     # Mises à jour uv + github-actions
├── src/cfp_reminders/
│   ├── cli.py              # Point d'entrée, orchestration
│   ├── fetcher.py          # GET all-cfps.json + filtre pays
│   ├── cache.py            # Cache JSON TTL 1h (~/.cache/cfp-reminders/)
│   ├── chat.py             # Message Google Chat + POST webhook
│   ├── meetown.py          # Snapshot JSON des CFP + POST Meetown (Bearer)
│   └── display.py          # Groupement urgence + tables Rich
├── tests/
│   ├── test_cli.py
│   ├── test_chat.py
│   ├── test_meetown.py     # Valide le snapshot contre le schéma
│   ├── test_fetcher.py
│   ├── test_cache.py
│   └── test_display.py
├── schemas/cfp-snapshot.schema.json  # Contrat JSON partagé avec Meetown
└── docs/plans/             # Design docs
```

## Modèle de données (API developers.events)

Chaque CFP est un `dict` avec notamment :

- `link` : URL de soumission
- `until` : deadline lisible (ex. "March-15-2026")
- `untilDate` : timestamp Unix ms
- `conf.name`, `conf.date`, `conf.hyperlink`, `conf.location` (ex. "Paris (France)")

Filtrage pays : `(France)` dans `conf.location`. Deadlines futures uniquement.

## Conventions de code

- **Typage** : annotations de type explicites, `list[dict]` plutôt que `List[dict]`
- **Imports** : `from __future__ import annotations` en tête de fichier
- **Tests** : `pytest`, `pytest-httpx` pour mocker les requêtes HTTP
- **Qualité** : Ruff (lint + format), pre-commit avant commit
- **Pas de dépendances lourdes** : rester léger (CLI)

## Commandes utiles

```bash
uv sync --all-groups       # Installer les dépendances (inclut dev)
uv run cfp-reminders       # Lancer le CLI
uv run cfp-reminders --chat --dry-run   # Aperçu du message Google Chat
uv run cfp-reminders --meetown --dry-run   # Aperçu du JSON envoyé à Meetown
uv run pytest              # Exécuter les tests
uv run pytest --cov=cfp_reminders   # Tests avec couverture
uv run ruff check . --fix  # Linter
uv run ruff format .       # Formatter
uv run pre-commit run --all-files   # Vérifier les hooks
uv tool install .          # Installer en outil global
```

## Flux de données

1. **cli.py** : lit le cache ou appelle `fetch_cfps()` ; en cas d’erreur réseau, tente le cache expiré
2. **fetcher.py** : GET `https://developers.events/all-cfps.json`, filtre par pays et date
3. **display.py** : groupe par urgence (0 à 7 j, 8 à 30 j, 31+ j), affiche des tables Rich
4. **chat.py** (avec `--chat`) : garde les CFP qui ferment dans `--days` jours, formate un message Google Chat, le poste sur `GOOGLE_CHAT_WEBHOOK_URL`. Ne poste rien si la liste est vide.
5. **meetown.py** (avec `--meetown`) : convertit tous les CFP ouverts du pays au format `schemas/cfp-snapshot.schema.json` et les envoie à `MEETOWN_WEBHOOK_URL` avec `MEETOWN_TOKEN`. Refuse d'envoyer une liste vide : Meetown remplace sa liste à chaque envoi, un snapshot vide (souvent une panne amont) l'effacerait.

## Règles

- **Webhook = secret** : l'URL porte une clé et un jeton. Ne jamais la logger ni la mettre dans un message d'erreur (`chat.py` coupe la cause avec `from None`). Elle vit dans le secret GitHub `GOOGLE_CHAT_WEBHOOK_URL`.
- **Jeton Meetown = secret** : même règle que le webhook, l'URL et le jeton ne sortent jamais dans un message d'erreur. HTTPS obligatoire, redirections refusées.
- **Contrat Meetown** : tout changement du snapshot passe d'abord par `schemas/cfp-snapshot.schema.json`, puis par l'équipe Meetown. `test_meetown.py` valide la sortie contre ce schéma.
- **Dépôt public** : aucun chemin local, aucune donnée client dans le code ni la doc.
- **Dates de test relatives** à `time.time()`, jamais codées en dur : une date fixe finit par passer et casse les tests.
- **Pas de tiret cadratin** dans les textes (message Chat, README, doc).

## Références

- Design : `docs/plans/2026-02-13-cfp-reminders-design.md`
- README : `README.md`
