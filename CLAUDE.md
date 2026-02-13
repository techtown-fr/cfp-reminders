# CFP Reminders — Contexte pour Claude

## Vue d'ensemble

CLI Python pour suivre les deadlines des **Call for Papers** (CFP) des conférences tech. Source : [developers.events](https://developers.events/all-cfps.json). Focus France par défaut.

## Stack technique

- **Python 3.12+** — `from __future__ import annotations` partout
- **uv** — gestion des dépendances et exécution
- **click** — CLI
- **httpx** — requêtes HTTP
- **rich** — affichage terminal (tables, couleurs)
- **pytest** + **pytest-httpx** + **pytest-cov** — tests et couverture
- **Ruff** — linter et formatter
- **pre-commit** — hooks Git (Ruff, trailing-whitespace, etc.)

## Structure du projet

```
cfp-reminders/
├── pyproject.toml          # uv, hatchling, Ruff, entry point cfp-reminders
├── .gitignore
├── .pre-commit-config.yaml
├── .github/
│   ├── workflows/ci.yml   # Lint (Ruff) + tests (pytest-cov)
│   └── dependabot.yml     # Mises à jour pip + github-actions
├── src/cfp_reminders/
│   ├── cli.py              # Point d'entrée, orchestration
│   ├── fetcher.py          # GET all-cfps.json + filtre pays
│   ├── cache.py            # Cache JSON TTL 1h (~/.cache/cfp-reminders/)
│   └── display.py          # Groupement urgence + tables Rich
├── tests/
│   ├── test_cli.py
│   ├── test_fetcher.py
│   ├── test_cache.py
│   └── test_display.py
└── docs/plans/             # Design docs
```

## Modèle de données (API developers.events)

Chaque CFP est un `dict` avec notamment :

- `link` — URL de soumission
- `until` — deadline lisible (ex. "March-15-2026")
- `untilDate` — timestamp Unix ms
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
3. **display.py** : groupe par urgence (0–7 j, 8–30 j, 31+ j), affiche des tables Rich

## Références

- Design : `docs/plans/2026-02-13-cfp-reminders-design.md`
- README : `README.md`
