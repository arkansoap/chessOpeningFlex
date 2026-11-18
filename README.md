# ChessOpeningFlex

Construire son **répertoire d'ouvertures à partir de ses propres parties**, puis le réviser.

L'app récupère mes parties sur chess.com et Lichess, les fusionne en un arbre de positions, repère
les coups que je répète et qui me coûtent, et m'aide à fixer un coup par position. Elle s'utilise
sur téléphone comme sur ordinateur, pour un seul joueur.

## Les cinq écrans

| Écran | Ce qu'on y fait |
|---|---|
| **Accueil** | Renseigner ses noms d'utilisateur, synchroniser ses parties, importer un PGN, lancer l'analyse Stockfish. |
| **Mes ouvertures** | Parcourir l'arbre de ses parties, position par position : coups joués, fréquence, gains / nulles / défaites, évaluation. Bilan par ouverture. L'étoile ☆ fait d'un coup son coup de répertoire. |
| **Mes fuites** | La liste des coups répétés que le moteur juge nettement inférieurs, les plus coûteux d'abord, avec la correction à mettre au répertoire. |
| **Répertoire** | Les trous (positions fréquentes sans coup choisi), les dernières parties avec l'endroit où elles quittent le répertoire, la liste des coups, un brouillon tiré de ses parties, l'import / export PGN. |
| **Entraînement** | Répétition espacée : la position s'affiche, on joue son coup. Les coups ratés en partie reviennent d'eux-mêmes. |

## Principes

- **Tout est indexé par position.** Les 40 premiers demi-coups de chaque partie sont enregistrés
  avec la clé de la position de départ de chaque coup. Deux parties qui arrivent à la même position
  par des ordres de coups différents se rejoignent dans l'arbre.
- **Le répertoire est une table « position → mon coup ».** Les réponses adverses ne sont pas
  stockées : une réponse est *couverte* quand la position qu'elle amène a un coup choisi.
- **Une fuite** est un coup joué au moins deux fois dans une position, qui perd au moins 5 points
  d'espérance de gain par rapport au meilleur coup du moteur (5 = imprécision, 10 = erreur,
  15 = gaffe — l'échelle de Lichess). Le classement tient compte du nombre de parties.
- **Répétition espacée par coup** : 4 h, 1 j, 3 j, 1 sem., 2 sem., 1 mois, 3 mois, 6 mois. Une
  erreur ramène le coup au départ.

## Stack

- **Backend** : FastAPI (Python 3.12), SQLAlchemy, Alembic, `python-chess`, SQLite.
- **Frontend** : React 18 + TypeScript (Vite), `react-chessboard`, `chess.js`.
- **Moteur** : Stockfish natif côté serveur pour l'analyse en lot, Stockfish WebAssembly dans le
  navigateur pour l'analyse en direct d'une position.

```
chessOpeningFlex/
├── backend/        API, services, migrations, tests
├── frontend/       interface React
├── data/           base SQLite (non versionnée)
├── deploy/         fichier de mot de passe pour un accès public
└── docs/           API.md, DEPLOY.md
```

## Démarrage en développement

### Backend

```bash
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python scripts/fetch_stockfish.py      # moteur natif (Linux x86-64), une fois
PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload --port 8000
```

La base `data/chessopeningflex.db` est créée et migrée au démarrage. Documentation interactive de
l'API : http://localhost:8000/docs.

### Frontend

```bash
cd frontend
nvm use 22
npm install          # télécharge aussi le moteur WebAssembly dans public/stockfish/
npm run dev          # http://localhost:5173, /api est relayé vers le port 8000
```

Si le backend écoute ailleurs : `API_TARGET=http://localhost:8031 npm run dev`.

### Docker

```bash
docker compose up --build        # http://localhost:8080
```

Depuis un téléphone sur le même réseau : `http://<adresse-de-la-machine>:8080`. Pour une adresse
publique en HTTPS (nécessaire pour installer l'app sur l'écran d'accueil), voir
[docs/DEPLOY.md](docs/DEPLOY.md).

## Moteur

- **Analyse en lot (serveur).** `scripts/fetch_stockfish.py` installe la version officielle de
  Stockfish dans `backend/.tools/`. À défaut, le binaire `stockfish` du `PATH` est utilisé, ou
  celui désigné par `STOCKFISH_PATH`. Sans moteur, l'app fonctionne mais « Mes fuites » reste vide.
- **Analyse en direct (navigateur).** Onglet « Moteur » de Mes ouvertures. La version
  multi-thread demande une page isolée (en-têtes `Cross-Origin-Opener-Policy` et
  `Cross-Origin-Embedder-Policy`, posés par Vite en développement et par Caddy en production) ;
  sinon la version mono-thread prend le relais.

## Statistiques Lichess

L'onglet « Lichess » de Mes ouvertures montre ce que jouent les joueurs de mon niveau. L'explorateur
d'ouvertures de Lichess exige une requête authentifiée : créer un jeton personnel sur
https://lichess.org/account/oauth/token (aucune permission à cocher) et le donner au backend dans
`LICHESS_TOKEN`. Sans jeton, l'onglet l'indique et le reste de l'app n'est pas affecté.

## Variables d'environnement (backend)

| Variable | Défaut | Rôle |
|---|---|---|
| `DATABASE_URL` | `sqlite:///<repo>/data/chessopeningflex.db` | Base de données. |
| `STOCKFISH_PATH` | recherche automatique | Binaire Stockfish pour l'analyse en lot. |
| `ANALYSIS_DEPTH` | `16` | Profondeur de l'analyse en lot. |
| `ANALYSIS_THREADS` | `4` | Threads du moteur. |
| `MAX_INDEXED_PLIES` | `40` | Demi-coups indexés par partie dans l'arbre. |
| `MAX_ANALYSED_PLIES` | `30` | Profondeur maximale des positions analysées. |
| `LICHESS_TOKEN` | aucun | Jeton pour les statistiques Lichess (et un import Lichess plus rapide). |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Origines autorisées en développement. |

Elles peuvent être placées dans `backend/.env`.

## Tests

```bash
cd backend && .venv/bin/python -m pytest -q      # services, API, migration
cd frontend && npx tsc -b && npm run build        # typage et build
```

## Migrations

Le schéma est géré par Alembic et appliqué au démarrage. Après une modification des modèles :

```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Licence

Ce projet est distribué sous licence [MIT](LICENSE). Stockfish (GPL-3.0) et les noms d'ouvertures
(CC0) restent soumis à leurs propres conditions : voir [THIRD-PARTY.md](THIRD-PARTY.md).
