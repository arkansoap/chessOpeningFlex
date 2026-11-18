# Déploiement

Deux façons d'utiliser l'app depuis un téléphone.

## 1. Sur le réseau de la maison

```bash
docker compose up -d --build
```

L'app répond sur `http://<adresse-de-la-machine>:8080` pour tous les appareils du réseau. Le port se
change avec `WEB_PORT`, le dossier de la base avec `DATA_PATH`.

Limite : en HTTP simple, le téléphone ne propose pas d'installer l'app sur l'écran d'accueil et le
moteur du navigateur tourne en mono-thread. Tout le reste fonctionne.

## 2. Sur une adresse publique, en HTTPS

Il faut un nom de domaine pointant sur le serveur et les ports 80 et 443 ouverts. Caddy obtient et
renouvelle le certificat tout seul.

L'app n'a pas de comptes : c'est un mot de passe HTTP, demandé par Caddy, qui la garde privée.

```bash
# 1. Créer le fichier de mot de passe
cp deploy/auth.caddy.example deploy/auth.caddy
docker run --rm caddy:2-alpine caddy hash-password --plaintext 'mon mot de passe'
#    coller le résultat dans deploy/auth.caddy, à la place de REPLACE_WITH_THE_HASH

# 2. Lancer
SITE_ADDRESS=echecs.exemple.org docker compose -f docker-compose.prod.yml up -d --build
```

`deploy/auth.caddy` n'est pas versionné. Sans ce fichier, `docker-compose.prod.yml` refuse de
démarrer : l'app ne se retrouve pas en ligne sans protection par oubli.

### Derrière un serveur web déjà en place

Si nginx ou un autre proxy occupe déjà les ports 80 et 443, garder `docker-compose.yml` (port 8080,
sans TLS) et faire suivre le domaine vers ce port. Le proxy en amont doit alors porter le
certificat, le mot de passe, et laisser passer les en-têtes `Cross-Origin-Opener-Policy` et
`Cross-Origin-Embedder-Policy` posés par Caddy.

## Installer l'app sur le téléphone

Une fois l'adresse HTTPS ouverte dans le navigateur :

- **Android (Chrome)** : menu ⋮ › « Installer l'application ».
- **iPhone (Safari)** : bouton Partager › « Sur l'écran d'accueil ».

L'app installée s'ouvre en plein écran. Hors connexion elle s'affiche, mais les données viennent
toujours du serveur : sans réseau, les écrans indiquent « Serveur injoignable ».

## Données et sauvegarde

Tout tient dans un fichier : `data/chessopeningflex.db` (parties, évaluations, répertoire, historique
d'entraînement). Le sauvegarder suffit. Les parties et les évaluations se reconstruisent par une
synchro et une analyse ; le répertoire et l'historique d'entraînement, non — l'export PGN du
répertoire (Répertoire › Outils) en donne une copie lisible ailleurs.

## Mise à jour

```bash
git pull
docker compose up -d --build        # ou la commande de production ci-dessus
```

Les migrations de base s'appliquent au démarrage du backend.

## Jeton Lichess

Pour l'onglet « Lichess » de Mes ouvertures, passer `LICHESS_TOKEN=...` dans l'environnement de la
commande `docker compose` (ou dans un fichier `.env` à la racine, non versionné).
