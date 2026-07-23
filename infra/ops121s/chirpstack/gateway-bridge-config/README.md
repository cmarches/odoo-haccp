# Configuration ChirpStack Gateway Bridge — à compléter

Fichier `chirpstack-gateway-bridge.toml` attendu ici (image
`chirpstack/chirpstack-gateway-bridge:4`), non fourni pour la même raison
que `../config/README.md` — à copier/adapter depuis le quickstart officiel
au moment du déploiement réel :
https://www.chirpstack.io/docs/chirpstack-gateway-bridge/

Ce service n'est nécessaire que le jour où un vrai gateway LoRaWAN physique
(RAK7268 ou équivalent) est branché sur le réseau — pas exercé par
`scripts/demo-simulate-sensor-chirpstack.py`, qui contourne toute cette
couche pour la démo.
