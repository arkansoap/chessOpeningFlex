# API — ChessOpeningFlex

Base URL : `/api/v1`. Toutes les réponses sont en JSON. Documentation interactive générée par FastAPI : `/docs` (Swagger) et `/redoc`.

## Health

### `GET /health`
Retourne `{"status": "ok"}`.

## chess.com

### `POST /api/v1/chesscom/import`
Importe des parties depuis l'API publique chess.com.

**Body :**
```json
{
  "username": "hikaru",
  "time_control": "rapid",
  "start_date": "2024-01",
  "end_date": "2024-06"
}
```
Tous les champs sauf `username` sont optionnels. `time_control` : `rapid` | `blitz` | `bullet` | `daily`. Les dates sont au format `YYYY-MM`.

**201** : tableau d'`ImportedGame`.

### `POST /api/v1/chesscom/upload-pgn`
Upload d'un PGN brut (texte/plain). Le body est le contenu PGN (plusieurs parties acceptées).

**201** : tableau d'`ImportedGame`.

## Analyse

### `POST /api/v1/analysis/variants`
Extrait la ligne principale d'un PGN.

**Body :**
```json
{ "pgn": "...", "color": "white", "min_depth": 0 }
```

**200** : tableau de `{ moves, starting_position, eco_code }`.

### `POST /api/v1/analysis/evaluate`
Évalue une position FEN avec Stockfish. Retourne `503` si le moteur n'est pas disponible.

**Body :** `{ "fen": "...", "depth": 15 }`
**200** : `{ fen, score, depth, best_move, mate }` (`score` en centipions, POV blancs).

## Répertoire

### `GET /api/v1/repertoire`
Liste tous les répertoires.

### `POST /api/v1/repertoire`
Crée un répertoire. **Body :** `{ "name": "...", "color": "white|black", "description": "...", "is_active": true }`

### `GET /api/v1/repertoire/{id}`
Récupère un répertoire + ses lignes.

### `PUT /api/v1/repertoire/{id}`
Met à jour un répertoire (champs optionnels : `name`, `description`, `is_active`).

### `DELETE /api/v1/repertoire/{id}` → 204

### `POST /api/v1/repertoire/line`
Ajoute une ligne. **Body :** `{ "repertoire_id": "...", "moves": "e4 e5 Nf3", "starting_position": "startpos", "depth": 3, "priority": 0, "comment": "..." }`

### `PUT /api/v1/repertoire/line/{id}`
Met à jour une ligne (`moves`, `comment`, `depth`, `priority`, `last_reviewed`).

### `DELETE /api/v1/repertoire/line/{id}` → 204

## Entraînement

### `POST /api/v1/training/session`
Enregistre une session terminée et met à jour les statistiques de mémorisation.

**Query params :** `repertoire_id`, `line_id`, `mode` (`random`|`sequential`|`full_variation`), `total_questions`, `correct_answers`, `time_spent?`, `score?`

### `GET /api/v1/training/question`
Génère une question d'entraînement pour une ligne.

**Query params :** `line_id`, `mode` (défaut `random`), `step` (défaut `0`, mode séquentiel).

**200** : `{ line_id, fen, expected_move, move_number, color_to_move }`

### `POST /api/v1/training/answer`
Vérifie une réponse. **Body :** `{ "line_id": "...", "move_played": "e4", "expected_move": "e4", "fen": "..." }`
**200** : `{ is_correct, expected_move, move_played }`

### `GET /api/v1/training/stats`
Récupère les statistiques de mémorisation.

**Query params :** `repertoire_id` **ou** `line_id` (au moins un requis).

**200** : tableau de `MemorizationStat`.
