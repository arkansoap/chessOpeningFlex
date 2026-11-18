# API — ChessOpeningFlex

Base : `/api/v1`. Réponses en JSON. Le détail des paramètres et des schémas est dans la
documentation interactive générée par FastAPI : `/docs` (Swagger) et `/redoc`.

## Paramètres communs

Les routes qui lisent mes parties acceptent les mêmes filtres en paramètres d'URL :

| Paramètre | Valeurs | Rôle |
|---|---|---|
| `color` | `white` \| `black` | Couleur que je jouais (obligatoire). |
| `time_class` | `bullet,blitz,rapid,classical,daily` | Cadences, séparées par des virgules. |
| `since`, `until` | `AAAA-MM-JJ` | Période. |
| `min_elo`, `max_elo` | entier | Classement de l'adversaire. |
| `platform` | `chesscom` \| `lichess` \| `pgn` | Origine des parties. |

Une position se désigne par `line` (coups SAN depuis le départ, séparés par des espaces :
`e4 e5 Nf3`) ou par `fen`.

## Parties

| Route | Rôle |
|---|---|
| `GET /accounts` · `PUT /accounts` | Mes noms d'utilisateur chess.com et Lichess. En changer un relance sa synchro de zéro. |
| `POST /sync` | Lance la synchronisation en tâche de fond. Corps : `{"platforms": [...], "months": 12}` (les deux facultatifs ; `months` borne le premier import). |
| `GET /sync/status` · `POST /sync/stop` | État de la tâche ; arrêt après l'étape en cours. |
| `GET /games/summary` | Nombre de parties par origine et par couleur. |
| `GET /games` | Parties récentes (`color`, `limit`). |
| `POST /games/upload-pgn` | Import d'un PGN envoyé tel quel dans le corps. `?player=` : mon nom dans le fichier. |

## Arbre de mes parties

| Route | Rôle |
|---|---|
| `GET /explorer/position` | Tout ce qui est connu d'une position : coups joués avec gains / nulles / défaites, évaluations, coup de répertoire, réponses couvertes, parties récentes. |
| `GET /explorer/openings` | Mes résultats par ouverture, regroupés par famille. |
| `GET /explorer/lichess` | Coups joués sur Lichess autour de `rating`. Répond `{"available": false}` sans `LICHESS_TOKEN`. |

## Analyse

| Route | Rôle |
|---|---|
| `GET /analysis/status` | Moteur disponible ou non, positions à analyser, état de la tâche. |
| `POST /analysis/run` · `POST /analysis/stop` | Analyse en lot des positions atteintes au moins `min_games` fois. `503` sans moteur. |
| `POST /analysis/evaluate` | Évaluation d'une position (mise en cache), du point de vue des blancs. |
| `GET /leaks` | Mes fuites : `min_games` (défaut 2), `min_loss` en points d'espérance de gain (défaut 5), `limit`. |

## Répertoire

| Route | Rôle |
|---|---|
| `GET /repertoire/{color}` | Résumé et liste des coups. |
| `PUT /repertoire/{color}/entry` | Choisit ou remplace mon coup dans une position : `{"line": "e4 e5", "move": "Nf3"}`. `400` si ce n'est pas à moi de jouer. |
| `PATCH /repertoire/entry/{id}` | Modifie la note d'un coup. |
| `DELETE /repertoire/entry/{id}` | Retire un coup. |
| `GET /repertoire/coverage` | Trous et écarts, agrégés sur mes parties (filtres communs). |
| `GET /repertoire/{color}/review` | Mes dernières parties, chacune avec l'endroit où elle quitte le répertoire. |
| `POST /repertoire/adopt` | Brouillon tiré de mes parties. `dry_run` (défaut `true`) ne fait que proposer. |
| `GET /repertoire/{color}/export.pgn` | Export en une partie avec variantes. |
| `POST /repertoire/{color}/import-pgn` | Import d'un PGN envoyé dans le corps. `?overwrite=true` remplace mes coups existants. |

## Entraînement

| Route | Rôle |
|---|---|
| `GET /training/next` | Prochaine question. `color` (`white`, `black`, `any`), `mode` (`due`, `all`), `exclude` (coup à ne pas reposer tout de suite). |
| `POST /training/answer` | Vérifie une réponse et replanifie le coup : `{"entry_id": "...", "move": "Nf3"}` ou `{"reveal": true}`. |
| `GET /training/stats` | Réponses par jour et état de chaque répertoire. |

## Santé

`GET /health` (hors préfixe) répond `{"status": "ok"}`.
