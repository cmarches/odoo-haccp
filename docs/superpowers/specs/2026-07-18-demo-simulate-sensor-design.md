# Spec — Script de démo `demo-simulate-sensor.py`

**Date :** 2026-07-18
**Statut :** Approuvé — prêt pour implémentation
**Auteur :** Brainstorming AIFluence Digital
**Périmètre :** Script CLI Python — émulation d'un capteur LHT65 pour démo client du pipeline HACCP IoT complet

---

## 1. Contexte et objectifs

### 1.1 Contexte

Le POC HACCP repose sur un pipeline validé : capteur LoRaWAN LHT65 → TTN (réseau LoRaWAN) → MQTT → vNode Automation (parser custom JS) → bridge Python (`infra/ops121s/odoo-bridge/bridge.py`) → Odoo (`quality.check` / `quality.alert`) → SMS (Free Mobile ou Twilio).

Pour les démos clients, ce pipeline a déjà été validé manuellement via la fonctionnalité **Simulate uplink** de la console TTN, qui injecte un faux uplink LoRaWAN directement dans le flux MQTT — exactement comme le ferait un vrai capteur. Cette manip manuelle reste disponible et n'est pas remplacée.

### 1.2 Objectif

Fournir un script reproductible qui déclenche la même simulation d'uplink via l'API TTN (au lieu de cliquer dans la console), pour pouvoir lancer une démo rapidement et de façon scriptée/répétable, sans dépendre d'un accès manuel à la console TTN pendant la présentation.

### 1.3 Ce qui ne change pas

- La console TTN garde son bouton **Simulate uplink** — les deux méthodes (manuelle et scriptée) appellent la même API TTN et restent utilisables indépendamment.
- Aucune modification du pipeline existant (vNode, bridge, Odoo) : le script se contente d'injecter un uplink au tout début de la chaîne, comme le ferait un vrai capteur.

---

## 2. Architecture

```
demo-simulate-sensor.py
        │  POST /api/v3/as/applications/{app_id}/devices/{device_id}/up/simulate
        ▼
   TTN (eu1.cloud.thethings.network)
        │  publie sur v3/{app_id}@ttn/devices/{device_id}/up
        ▼
   MQTT broker TTN
        │  souscription vNode (MqttClient, parser custom)
        ▼
   vNode Automation (OPS121S) → tags HACCP
        │  RestApiClient
        ▼
   bridge.py (127.0.0.1:5001) → quality.check / quality.alert
        │
        ▼
   Odoo 19 EE (odoo19e_dev) — SMS si hors seuil
```

Le script n'interagit qu'avec l'API TTN. Tout le reste du pipeline est déjà en place et n'est pas touché.

---

## 3. Script `scripts/demo-simulate-sensor.py`

### 3.1 Conventions

- Python 3, stdlib uniquement (`urllib`, `json`, `argparse`) — même style que `bridge.py` et `test-odoo-api.py`, pas de dépendance à installer.
- Emplacement : `scripts/demo-simulate-sensor.py`

### 3.2 Devices connus (aide-mémoire intégrée)

| device_id | Paramètre | Seuil | Valeur de démo suggérée (hors seuil) |
|-----------|-----------|-------|----------------------------------------|
| `lht65-frigo-positif` | `temperature_1` | ≤ 4°C | `12.0` |
| `lht65-congelateur` | `temperature_1` | ≤ -15°C | `-5.0` |
| `lht65-stockage-sec` | `humidity` | ≤ 75% | `90.0` |

### 3.3 CLI

```
demo-simulate-sensor.py --device <device_id> --value <valeur> [--field temperature_1|humidity] [--app-id ID] [--region eu1]
demo-simulate-sensor.py --list-devices
```

- `--device` : device_id TTN (les 3 valeurs connues ci-dessus, ou tout autre texte libre)
- `--value` : valeur numérique à injecter
- `--field` : `temperature_1` (défaut) ou `humidity`
- `--list-devices` : affiche le tableau des devices connus avec leurs seuils, puis quitte
- `--app-id` : optionnel, défaut = variable d'env `TTN_APP_ID` ou `haccp-restaurant-poc`
- `--region` : optionnel, défaut = variable d'env `TTN_REGION` ou `eu1`

### 3.4 Variables d'environnement

| Variable | Requis | Défaut |
|----------|--------|--------|
| `TTN_API_KEY` | oui | — |
| `TTN_APP_ID` | non | `haccp-restaurant-poc` |
| `TTN_REGION` | non | `eu1` |

Si `TTN_API_KEY` est absent, le script s'arrête avec un message explicatif :
> Clé API TTN manquante. Génère-en une dans la console TTN : Application → API keys → droit "Write application traffic (uplink and downlink)", puis `export TTN_API_KEY=...`.

### 3.5 Comportement

1. Valide les arguments et la présence de `TTN_API_KEY`.
2. Construit l'URL : `https://{region}.cloud.thethings.network/api/v3/as/applications/{app_id}/devices/{device_id}/up/simulate`
3. Construit le corps JSON au format `ApplicationUp` attendu par l'API TTN — structure minimale avec `end_device_ids` (device_id + application_ids) et `uplink_message.decoded_payload` contenant `{field: value}`. Le détail exact du schéma (champs obligatoires/optionnels comme `f_port`, `rx_metadata`) sera vérifié et ajusté lors du premier appel réel pendant l'implémentation — c'est le point d'incertitude identifié en brainstorming.
4. Envoie la requête `POST` avec `Authorization: Bearer {TTN_API_KEY}`.
5. Affiche le code retour HTTP et confirme l'envoi (mode single-shot : une seule mesure hors-seuil, pas de séquence).
6. Rappelle à l'écran les étapes à observer en direct pendant la démo (Odoo → `quality.check`/`quality.alert`, téléphone → SMS), sans vérification automatique côté Odoo — l'utilisateur observe en direct.

### 3.6 Gestion d'erreurs

- `TTN_API_KEY` absent → message explicatif, exit 1, pas d'appel réseau.
- Erreur HTTP TTN (4xx/5xx) → afficher le code, le corps de la réponse (pour diagnostiquer un souci de schéma ou de droits), exit 1.
- Erreur réseau (timeout, DNS) → message clair, exit 1.

---

## 4. Hors périmètre

- Vérification automatique côté Odoo (poll XML-RPC) — explicitement écarté, l'utilisateur observe en direct pendant la démo.
- Séquence multi-mesures (normal → dérive progressive) — explicitement écarté, une seule mesure hors-seuil suffit.
- Modification du pipeline existant (vNode, bridge, parser) — aucune touche prévue.

---

## 5. À retester lors de l'implémentation

Tout le pipeline (TTN Simulate manuel ET scripté → MQTT → vNode → bridge → Odoo → SMS) est **à retester** après l'implémentation du script, l'environnement ayant pu dériver depuis la dernière validation (base `odoo19e_dev` récemment réactivée, cf. session précédente).

---

## 6. Références

| Élément | Valeur |
|---------|--------|
| Application TTN | `haccp-restaurant-poc` |
| Région TTN | `eu1.cloud.thethings.network` |
| Devices | `lht65-frigo-positif`, `lht65-congelateur`, `lht65-stockage-sec` |
| Bridge Odoo | `infra/ops121s/odoo-bridge/bridge.py` — endpoint `POST 127.0.0.1:5001/quality-check` |
| Config vNode MqttClient | `infra/ops121s/vnode/config/MqttClient-config.n3c` |
| Instance Odoo dev | `http://192.168.1.182:8029` (odoo19e_dev) |
