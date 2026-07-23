# Configuration ChirpStack — à compléter avant le premier déploiement

Ce dossier doit contenir les fichiers `.toml` de configuration de ChirpStack
(app server + network server, image `chirpstack/chirpstack:4`) : au minimum
`chirpstack.toml` et un fichier de plan de fréquence régional
(`region_eu868.toml` pour l'Europe).

**Ce contenu n'est volontairement pas fourni ici** — le schéma exact dépend
de la version de ChirpStack réellement déployée et évolue avec le produit.
À copier/adapter depuis le quickstart officiel ChirpStack (docker-compose)
au moment du déploiement réel sur l'OPS121S, pas avant :
https://www.chirpstack.io/docs/chirpstack/getting-started/docker.html

Points à configurer en particulier (déjà connus de ce projet) :
- Connexion Postgres : host `postgres`, db `chirpstack`, user `chirpstack`,
  password = `CHIRPSTACK_POSTGRES_PASSWORD` (voir `infra/ops121s/.env`).
- Connexion Redis : host `redis`.
- Intégration MQTT : host `mosquitto` (le broker déjà présent dans ce
  docker-compose), pas un nouveau broker.
- Plan de fréquence : EU868 (cohérent avec les capteurs LHT65 déjà en jeu
  dans ce POC).

Voir `docs/operations/chirpstack-deploiement-ops121s.md` pour la procédure
complète de déploiement (tenant, application, device profile + codec,
provisionnement des devices).
