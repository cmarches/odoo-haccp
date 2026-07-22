# Architecture actuelle — Réseau

> Suite de `architecture-ops121s-vnode.md` et `architecture-odoo.md`. Comme pour ces deux documents, on distingue ici l'**état réel du POC démo** (ce qui tourne aujourd'hui) de l'**architecture cible production** décrite dans `dream-machine-se-config.md`, `rak7268-setup.md` et `ttn-setup.md` — ces trois fichiers restent la procédure de référence pour un déploiement client, mais rien de leur contenu réseau (VLANs, Dream Machine SE, gateway physique) n'est déployé à ce jour.

## 1. Vue d'ensemble — deux couches réseau

```
                     ┌─────────────────────────────┐
                     │   TTN — eu1.cloud.thethings  │   Cloud (LNS), hors LAN
                     │   .network                    │
                     └───────────────┬───────────────┘
                                     │ MQTT TLS 8883 (sortant, LAN → cloud)
                                     │ + API HTTPS /up/simulate (démo)
┌────────────────────────────────────┴────────────────────────────────────┐
│                    LAN actuel — 192.168.1.0/24 (réseau existant,         │
│                    PAS le VLAN IoT cible)                                │
│                                                                            │
│   192.168.1.101  OPS121S (vNode + bridge)                                │
│   192.168.1.182  Serveur Odoo (4 instances Docker)                       │
│   192.168.1.174  Cible sauvegarde restic                                 │
│   192.168.1.31   Imprimante Zebra OXHOO TLP200 (ZPL, port 9100)          │
│   192.168.1.1    Box/routeur du réseau existant (pas un Dream Machine SE)│
└────────────────────────────────────────────────────────────────────────┘
```

Aucun matériel réseau IoT dédié n'est encore déployé : pas de Dream Machine SE, pas de gateway LoRaWAN RAK7268, pas de VLANs. Le POC tourne entièrement sur le réseau local existant, à plat.

## 2. TTN — couche cloud (réellement en service)

C'est la seule partie de la couche "réseau" de `docs/operations/` qui est **effectivement configurée et utilisée** aujourd'hui.

| Paramètre | Valeur |
|---|---|
| Région | eu1.cloud.thethings.network |
| Application ID | `haccp-restaurant-poc` |
| MQTT host | `eu1.cloud.thethings.network:8883` (TLS) |
| MQTT username | `haccp-restaurant-poc@ttn` |
| Topic uplink | `v3/haccp-restaurant-poc@ttn/devices/+/up` |

### Devices déclarés vs réellement provisionnés

| Device ID TTN | Affectation prévue | État réel |
|---|---|---|
| `lht65-frigo-positif` | Frigo positif | **Seul device réellement enregistré dans TTN**, utilisé pour toutes les démos |
| `lht65-congelateur` | Congélateur | Placeholder — identifiant utilisé dans `scripts/demo-simulate-sensor.py`, jamais enregistré côté TTN |
| `lht65-stockage-sec` | Stockage sec | Placeholder — idem |

Simuler un uplink sur les deux devices placeholders échouera tant qu'ils ne sont pas enregistrés dans la console TTN (`ttn-setup.md` §4 décrit la procédure d'enregistrement OTAA via Device Repository, à suivre le jour où les capteurs physiques arrivent).

### Payload formatter — piège déjà rencontré

`ttn-setup.md` recommande le formatter standard du Device Repository (codec Dragino LHT65). En pratique, ce codec **crashe sur les octets du capteur externe** (`7FFFFFFF01`), voir `architecture-ops121s-vnode.md` §3.1. Le formatter réellement actif sur `lht65-frigo-positif` est un formatter **custom au niveau device**, réécrit pour décoder 6 bytes de `frm_payload` (batterie masquée 14 bits, température signée /100, humidité /10) sans jamais toucher aux bytes du capteur externe.

### Gestion des clés API — piège d'interface

Le secret d'une clé API TTN n'est affiché **qu'une seule fois**, à l'écran de confirmation juste après création (texte masqué, pas de bouton copier dédié). Une fois ce dialogue fermé, il n'est plus jamais récupérable — il faut recréer une clé. Une clé `haccp-restaurant-poc-apikey` (droits "All application rights", créée 2026-05-19) a son secret perdu et ne doit pas être recherchée. La clé active actuellement est `demo-simulate-sensor`, créée avec le seul droit nécessaire ("write uplink application traffic"), pour le script de démo.

## 3. Génération d'uplinks sans gateway physique

Faute de gateway RAK7268 déployée, les démos passent par l'API TTN plutôt que par une vraie radio LoRaWAN :

```
scripts/demo-simulate-sensor.py → POST .../up/simulate (frm_payload encodé) → formatter uplink device
  → MQTT → vNode MqttClient (voir architecture-ops121s-vnode.md)
```

Le script encode le payload en `frm_payload` (pas en `decoded_payload`) pour exercer le vrai formatter TTN, donc l'ensemble de la chaîne de décodage — pas seulement le point d'entrée MQTT.

## 4. Architecture réseau cible production (non déployée)

Décrite intégralement dans `dream-machine-se-config.md` et `rak7268-setup.md`. Résumé pour référence :

- **Routeur** : Ubiquiti Dream Machine SE, dual WAN (Fibre + 4G/LTE SIM 1NCE en failover 30s).
- **VLANs** :
  | VLAN | Nom | Subnet | Usage |
  |---|---|---|---|
  | 10 | IoT_HACCP | 10.10.10.0/24 | OPS121S (.10), RAK7268 (.11) — inter-VLAN routing désactivé |
  | 20 | WiFi_Restaurant | 10.10.20.0/24 | Wi-Fi client, isolé du VLAN IoT par règle firewall |
  | 30 | Management | 10.10.30.0/24 | IPs fixes, pas de DHCP |
- **Gateway LoRaWAN** : RAK7268 indoor, EU868, PoE (port 1 du Dream Machine SE), connecté à TTN en Basics Station (`wss://eu1.cloud.thethings.network:8887`).
- **Isolation** : règle firewall explicite bloquant IoT → Wi-Fi.

Ce schéma s'active au moment d'un déploiement client réel — jusque-là, `192.168.1.101` (OPS121S) et les autres IPs `192.168.1.x` restent les adresses à utiliser pour toute intervention sur le POC.

## Écarts avec la documentation existante

| Aspect | Doc existant | État réel POC |
|---|---|---|
| Routeur/VLANs | Dream Machine SE, 3 VLANs isolés | Réseau plat existant `192.168.1.0/24` |
| Gateway LoRaWAN | RAK7268 physique EU868 | Absente — uplinks simulés via API TTN |
| Adressage OPS121S | `10.10.10.10` (VLAN IoT) | `192.168.1.101` |
| Capteurs TTN | 3 devices enregistrés (frigo, congélateur, stockage) | 1 seul réellement enregistré (`lht65-frigo-positif`) |
| Payload formatter | Codec Device Repository standard | Formatter custom device-level (le codec standard crashe sur ce capteur) |
