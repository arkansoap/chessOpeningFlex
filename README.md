# ChessOpeningFlex

Application de **construction et d'entraînement de répertoires d'ouvertures d'échecs**.

Deux grandes parties :
1. **Construction du répertoire** : import de parties (chess.com ou PGN), analyse Stockfish, extraction/sélection/nettoyage des lignes.
2. **Entraînement** : révision des lignes mémorisées (mode aléatoire, enchaîné, variante complète) avec statistiques.

## Stack

- **Backend** : FastAPI (Python 3.12), SQLAlchemy, Pydantic, `python-chess`, `stockfish`.
- **Frontend** : React 18 + TypeScript (Vite), `react-chessboard`, `chess.js`, `axios`, `recharts`.
- **Base de données** : SQLite par défaut (configurable vers PostgreSQL via `DATABASE_URL`).
- **Moteur d'analyse** : Stockfish (intégré via `python-chess` / `stockfish`).

## Structure

```
chessOpeningFlex/
├── backend/        # API FastAPI + logique métier + services
├── frontend/       # Interface React + TypeScript
├── data/           # Données (PGN bruts/traîtés, base SQLite)
├── docs/           # Documentation (API.md)
└── docker-compose.yml
```

## Démarrage rapide (développement local)

### Backend

```bash
cd backend
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

La base SQLite et les tables sont créées automatiquement au démarrage (`data/chessopeningflex.db`).
OpenAPI : http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Le serveur de dev proxy `/api` vers `http://localhost:8000` (voir `vite.config.ts`).

### Docker

```bash
docker compose up --build
```

## Variables d'environnement (backend)

| Variable           | Défaut                              | Description                              |
|--------------------|-------------------------------------|------------------------------------------|
| `DATABASE_URL`     | `sqlite:///.../data/chessopeningflex.db` | URL SQLAlchemy.                     |
| `STOCKFISH_PATH`   | `None` (recherche `stockfish` sur PATH) | Chemin du binaire Stockfish.        |
| `STOCKFISH_DEPTH`  | `15`                                | Profondeur d'analyse par défaut.         |
| `CORS_ORIGINS`     | `http://localhost:5173,...`          | Origines CORS autorisées (séparées par `,`). |

## Tests backend

```bash
cd backend
python -m pytest
```

## Migrations (Alembic)

Le schéma de base de données est géré par Alembic. Les migrations s'appliquent
automatiquement au démarrage de l'application (`run_migrations` dans le
lifespan FastAPI), avec un repli sur `create_all` si Alembic n'est pas disponible.

Commandes manuelles (depuis `backend/`) :

```bash
# Appliquer toutes les migrations en attente
alembic upgrade head

# Revenir à l'état précédent
alembic downgrade -1

# Générer une migration après modification des modèles
alembic revision --autogenerate -m "description du changement"
```

## Statut

- **Backend** : fonctionnel (modèles, services chess.com/analyse/répertoire/entraînement, endpoints API, tests, migrations Alembic).
- **Frontend** : composants UI interactifs implémentés (échiquier `react-chessboard` + `chess.js`, uploader PGN, import chess.com, analyseur de variantes, sélecteur de lignes, arborescence du répertoire, éditeur de lignes, mode entraînement, tableau de bord statistiques `recharts`).
- **CI** : GitHub Actions (tests backend + migration, typecheck + build frontend).
- **À venir** : tests frontend, optimisation du bundle frontend.

## Roadmap

- [x] Composants UI interactifs (react-chessboard, uploader PGN, arborescence du répertoire)
- [x] Page d'entraînement complète (modes aléatoire / enchaîné / variante complète)
- [x] Tableau de bord statistiques (recharts)
- [x] Migrations Alembic
- [x] CI/CD (build frontend + tests backend + check migration)
- [ ] Tests frontend
- [ ] Optimisation du bundle frontend (code-splitting)

