**Spec — Architecture IoT HACCP Restaurant**  
**Date :** 2026-05-18  
   
 **Statut :** Brouillon v5 — Toutes les questions ouvertes résolues (2026-05-18)  
   
 **Auteur :** Brainstorming AIFluence Digital  
   
 **Périmètre :** POC restaurant unique · Pilote évolutif multi-sites  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSPBCj7fFjsymJHAjAU2QtIq6DIzW7UHAMBfnGt1V8fXEwAAXrsexNkF4H1/HJoAAAAASUVORK5CYII=)  
** **  
**1. Contexte et objectifs**  
**1.1 Contexte**  
Ce projet vise à construire une architecture de collecte de données IoT pour la surveillance HACCP  
   
 (Hazard Analysis and Critical Control Points) d'un restaurant. Le premier déploiement est un POC  
   
 de démonstration conçu dès le départ pour être extensible à un réseau multi-sites (franchise, chaîne).  
La certification HACCP impose une surveillance continue et traçable des températures des équipements  
   
 de conservation (froid positif, froid négatif), avec archivage réglementaire et gestion documentée  
   
 des non-conformités.  
**1.2 Objectifs du POC**  
- Collecter en continu les températures des équipements frigorifiques via capteurs LoRaWAN  
- Détecter en temps réel tout dépassement de seuil critique  
- Alerter le responsable en moins de 30 secondes, y compris la nuit  
- Créer automatiquement les enregistrements HACCP dans Odoo (Module Qualité)  
- Produire des rapports PDF réglementaires exportables pour les audits  
- Démontrer l'architecture à des clients potentiels (format démo)  
**1.3 Données surveillées**  
| | | | |  
|-|-|-|-|  
| **Mesure** | **Équipement cible** | **Seuil critique** | **Priorité** |   
| Température froid positif | Frigos, réfrigérateurs | > 4°C | Primaire |   
| Température froid négatif | Congélateurs | > −15°C | Primaire |   
| Température + Humidité | Stockage sec, cave | Humidité > 80% HR | Secondaire |   
| Température chaud | Bain-marie, armoire chauffante | < 63°C | Phase 2 |   
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OQQmAABRAsSd40A5GMORPYEt7WMGbCFuCLTNzVFcAAPzFvVZbdX49AQDgtf0BSrIDUgOg4eAAAAAASUVORK5CYII=)  
** **  
**2. Architecture globale**  
**2.1 Vue en couches**  
┌─────────────────────────────────────────────────────────┐  
 │  COUCHE 4 — Applicative                                  │  
 │  Odoo VPS (on-premise cloud)                             │  
 │  Module Qualité · Non-conformités · Rapports HACCP       │  
 └──────────────────────┬──────────────────────────────────┘  
                        │ JSON-RPC / REST HTTPS  
                        │ Sync asynchrone · Résilient offline  
 ┌──────────────────────┴──────────────────────────────────┐  
 │  COUCHE 3 — Edge Computing                               │  
 │  OPS121S · Ubuntu 20.04 LTS · Docker                    │  
 │  vNode Automation · Mosquitto · InfluxDB · Portainer     │  
 └──────────────────────┬──────────────────────────────────┘  
                        │ MQTT over TLS 1.3  
                        │ (via Dream Machine SE — dual WAN)  
 ┌──────────────────────┴──────────────────────────────────┐  
 │  COUCHE 2 — Réseau                                       │  
 │  Dream Machine SE (dual WAN) · RAK7268 Gateway           │  
 │  TTN LoRaWAN Network Server                              │  
 └──────────────────────┬──────────────────────────────────┘  
                        │ LoRaWAN 868 MHz · AES-128  
 ┌──────────────────────┴──────────────────────────────────┐  
 │  COUCHE 1 — Capteurs IoT                                 │  
 │  3× Dragino LHT65 (température + humidité)               │  
 └─────────────────────────────────────────────────────────┘  
   
**2.2 Principe de résilience**  
La liaison vNode ↔ Odoo transite par un routeur Ubiquiti Dream Machine SE équipé de deux accès WAN  
   
 (Fibre ISP + 4G/LTE). La disponibilité combinée atteint **99.999%** (< 5 minutes d'indisponibilité  
   
 par an), ce qui rend Odoo suffisamment fiable pour être le canal principal d'alertes.  
vNode conserve un **fallback local** : si l'API Odoo est injoignable, les alertes sont envoyées  
   
 directement (push ntfy + SMS), et les mesures sont bufferisées en SQLite sur l'OPS121S jusqu'au  
   
 retour de la connexion.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OQQ2AQBAAsSHhiQI0IWp9ngBsYIEfIWkVdJuZs5oAAPiLe6+O6vp6AgDAa+sBhYwEOqBD7p8AAAAASUVORK5CYII=)  
** **  
**3. Composants matériels**  
**3.1 Capteurs IoT — Dragino LHT65**  
| | |  
|-|-|  
| **Caractéristique** | **Valeur** |   
| Protocole | LoRaWAN Class A · EU868 |   
| Mesures | Température (interne + sonde externe) · Humidité relative |   
| Précision température | ±0.3°C |   
| Alimentation | 2× AA lithium (durée de vie : 5–8 ans) |   
| Fréquence de mesure | 1 mesure toutes les 10 minutes (configurable) |   
| Spreading Factor | SF9–SF10 (recommandé pour chambres froides) |   
| Prix unitaire | ~40€ |   
| Quantité POC | 3 unités |   
   
**Affectation des capteurs :**  
- LHT65 #1 — Frigo positif (sonde externe plongeante, −40°C/+85°C)  
- LHT65 #2 — Congélateur (sonde externe plongeante)  
- LHT65 #3 — Stockage sec (capteur interne température + humidité)  
**3.2 Gateway LoRaWAN — RAK7268**  
| | |  
|-|-|  
| **Caractéristique** | **Valeur** |   
| Type | Gateway indoor 8 canaux |   
| Fréquence | EU868 |   
| Connexion backhaul | Ethernet RJ45 (principal) |   
| Alimentation | PoE 802.3af (fourni par Dream Machine SE) |   
| Portée | Couvre l'intégralité d'un restaurant standard |   
| Prix | ~120€ |   
   
***Note production :*** * La version RAK7268C ajoute un module 4G intégré (~160€), permettant*  
 *  
 un second failover au niveau de la gateway elle-même, indépendant du router.*  
**3.3 Routeur — Ubiquiti Dream Machine SE**  
| | |  
|-|-|  
| **Caractéristique** | **Valeur** |   
| WAN 1 | Fibre / ADSL ISP principal |   
| WAN 2 | 4G/LTE via SIM IoT M2M |   
| Failover | Automatique < 30 secondes |   
| Switch intégré | 8 ports dont PoE (alimente RAK7268 sans adaptateur) |   
| Wi-Fi | Wi-Fi 6 intégré (tablettes, smartphones) |   
| VLANs | Oui — segmentation IoT / Wi-Fi / Management |   
| Firewall | IDS/IPS intégré |   
| Prix indicatif | ~450–500€ |   
   
   
**Segmentation VLAN :**  
| | | |  
|-|-|-|  
| **VLAN** | **Réseau** | **Équipements** |   
| IoT | 10.10.10.0/24 | RAK7268 Gateway · OPS121S |   
| Wi-Fi | 10.10.20.0/24 | Tablettes · Smartphones · Dashboard |   
| Management | 10.10.30.0/24 | SSH · UniFi · Administration |   
   
**3.4 Edge Computer — OPS121S**  
| | |  
|-|-|  
| **Caractéristique** | **Valeur** |   
| Format | Module OPS (Open Pluggable Specification) industriel |   
| Processeur | Intel Core i5-12420H (12e génération) |   
| RAM | 8 GB |   
| Stockage | 256 GB SSD NVMe |   
| Connectivité | 2× LAN Gigabit · USB · HDMI |   
| Système d'exploitation | Ubuntu 20.04 LTS |   
| Runtime | Docker Engine |   
| Consommation | 15–35 W sous charge |   
| Statut | Disponible (déjà en possession) |   
   
***Note :*** * Ubuntu 20.04 LTS est hors support standard depuis avril 2025. La migration vers*  
 *  
 22.04 LTS est recommandée avant tout déploiement en production client.*  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OYQ1AABSAwY9JoICqL4Z8Ikiggn9mu0twy8wc1RkAAH9xbdVa7V9PAAB47X4A9CgEJQFjJ/EAAAAASUVORK5CYII=)  
** **  
**4. Architecture réseau**  
**4.1 Flux complet de données**  
[LHT65 #1,#2,#3]  
       │ LoRaWAN 868 MHz · AES-128 · SF9 · 1/10 min  
       ▼  
 [RAK7268 Gateway] ──PoE Ethernet──► [Dream Machine SE]  
                                            │  
                               ┌────────────┴────────────┐  
                               │ WAN1 : Fibre ISP        │  
                               │ WAN2 : 4G/LTE (failover)│  
                               └────────────┬────────────┘  
                                            │ Internet  
                                            ▼  
                               [TTN — eu1.cloud.thethings.network]  
                               LoRaWAN Network Server · Décodage payload  
                                            │ MQTT over TLS 1.3 · port 8883  
                                            ▼  
                               [OPS121S — Mosquitto MQTT Broker]  
                                            │  
                                     [vNode Automation]  
                                ┌───────────┴───────────┐  
                                │                       │  
                       [InfluxDB local]        [API Odoo JSON-RPC]  
                       Time-series · buffer     └─► [Odoo VPS]  
                                                   Module Qualité  
   
**4.2 LoRaWAN Network Server (LNS)**  
**POC :** The Things Network (TTN) — gratuit, zéro installation, console web intuitive.  
**Production :** Migration vers Chirpstack auto-hébergé sur le VPS Odoo (Docker Compose).  
   
 Avantages : données 100% locales, aucune limite de messages, intégration MQTT directe.  
**4.3 Sécurité réseau**  
| | |  
|-|-|  
| **Segment** | **Chiffrement** |   
| Capteurs → Gateway | AES-128 natif LoRaWAN (AppSKey + NwkSKey) |   
| Gateway → TTN | TLS 1.3 (Semtech Packet Forwarder) |   
| TTN → vNode (MQTT) | TLS 1.3 · port 8883 · authentification par token |   
| vNode → Odoo (API) | HTTPS · TLS 1.3 · authentification API key |   
| Administration (SSH) | VLAN Management isolé · clé publique uniquement |   
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNhZscYahheJwqQgQU2QtIq6DIze3UGAMBf3Gu1VcfXEwAAXrseoqcEQXyAWBgAAAAASUVORK5CYII=)  
** **  
**5. Stack logicielle — OPS121S**  
**5.1 Système**  
- **OS :** Ubuntu 20.04 LTS (Server, sans interface graphique)  
- **Runtime :** Docker Engine + Docker Compose v2  
- **vNode :** déployé dans Docker (cohérence architecturale, gestion via Portainer)  
- **Administration :** SSH (clé publique) + Portainer (interface web)  
***Réserve licences vNode en production :*** * les licences vNode sont liées à un identifiant* * * *machine. En Docker, forcer un MAC address fixe (* *--mac-address* *) pour stabiliser l'empreinte* * * *matérielle. À confirmer avec Vester avant tout achat de licence en environnement containerisé.*  
**5.2 vNode Automation — Détail du produit**  
**Éditeur :** Vester Business S.L. — plateforme IIoT Edge (Industry 4.0)  
   
 **Site :** vnodeautomation.com  
   
 **Déploiement :** Container Docker (MAC address fixe) · OPS121S Ubuntu 20.04  
**Architecture modulaire :** vNode fonctionne par modules achetés séparément.  
   
 Les deux modules nécessaires pour notre architecture :  
| | | |  
|-|-|-|  
| **Module** | **Rôle dans le POC** | **Licence** |   
| **MQTT Client** | Abonnement MQTT → TTN (ou Mosquitto local) · réception payloads capteurs | Remote Tag |   
| **REST API Client** | Push données → API Odoo (JSON-RPC/REST) · création enregistrements qualité | Remote Tag |   
   
**Modèle de licence :**  
| | | |  
|-|-|-|  
| **Type** | **Prix unitaire** | **Usage** |   
| Remote Tag | ~1 375 – 1 595 € | Données générées localement sur vNode (notre cas) |   
| Central Tag | ~4 125 – 4 990 € | Données reçues d'autres instances vNode distantes |   
   
***POC :*** * essai gratuit 30 jours disponible — suffisant pour la démonstration complète.*  
 *  
 * ***Production :*** * budget licence ~2 750 – 3 200 € pour les 2 modules (remises volume possibles dès 10 tags).*  
**Absence de module LoRaWAN natif :** vNode ne parle pas directement LoRaWAN. TTN  
   
 fait office de passerelle LoRaWAN→MQTT, et le module MQTT Client de vNode s'y connecte.  
   
 C'est l'architecture retenue — aucun développement spécifique requis.  
**5.3 Stack Docker (services complémentaires à vNode)**  
# docker-compose.yml (schématique)  
 services:  
   vnode:       # vNode Automation · binaire Linux x64 · MAC address fixe  
   mosquitto:   # Broker MQTT local · eclipse-mosquitto:2.x  
   influxdb:    # Time-series DB · influxdb:2.x  
   portainer:   # UI gestion Docker · portainer/portainer-ce  
   
| | | | |  
|-|-|-|-|  
| **Service** | **Déploiement** | **Rôle** | **RAM estimée** |   
| vNode Automation | Docker (MAC fixe) | Ingestion · règles HACCP · alertes · sync Odoo | ~512 MB |   
| mosquitto | Docker | Broker MQTT local · découple TTN ↔ vNode | ~64 MB |   
| influxdb | Docker | Historique time-series local · backup VPS | ~512 MB |   
| portainer | Docker | UI Docker web · monitoring · logs | ~128 MB |   
   
   
**Total RAM utilisé : ~1.3 GB / 8 GB disponibles.** Marge suffisante pour ajouter Chirpstack en production.  
**5.4 vNode Automation — Responsabilités**  
1. **Ingestion** : abonnement MQTT au broker Mosquitto · réception des payloads TTN décodés  
2. **Normalisation** : mapping JSON TTN → format mesure interne (device_id, timestamp, valeur, unité)  
3. **Évaluation des règles HACCP** : comparaison des valeurs aux seuils configurés par zone/équipement  
4. **Déclenchement d'alertes** : appel API Odoo (chemin principal via REST API Client module)  
5. **Fallback local** : si API Odoo injoignable, envoi direct push ntfy + SMS  
6. **Buffer offline** : stockage SQLite local des mesures non synchronisées · sync à la reconnexion  
7. **Persistance InfluxDB** : écriture de chaque mesure pour l'historique local  
**5.5 Format des données reçues (TTN → MQTT)**  
{  
   "end_device_ids": { "device_id": "lht65-frigo-1" },  
   "received_at": "2026-05-18T03:14:22Z",  
   "uplink_message": {  
     "decoded_payload": {  
       "temperature_1": 5.8,  
       "humidity": 62.3,  
       "battery_voltage": 3.1  
     },  
     "rx_metadata": [{ "rssi": -87, "snr": 7.5 }]  
   }  
 }  
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OMQ2AABAAsSNBACPq8MH2NpGACyywEZJWQZeZ2aszAAD+4l6rrTq+ngAA8Nr1AL/KBEe6dElaAAAAAElFTkSuQmCC)  
**6. Stratégie d'alertes**  
**6.1 Principe général**  
Avec le Dream Machine SE (dual WAN, uptime 99.999%), **Odoo est le canal d'alertes principal**.  
   
 vNode assure un fallback local pour le cas exceptionnel d'indisponibilité Odoo.  
**6.2 Flux d'escalade**  
| | | | |  
|-|-|-|-|  
| **Étape** | **Délai** | **Action** | **Canal** |   
| 1 — Détection | t + 0s | vNode détecte dépassement de seuil | Local OPS121S |   
| 2 — Notification Odoo | t + 5s | vNode push événement → Odoo API | JSON-RPC HTTPS |   
| 3 — Alerte Niveau 1 | t + 10s | Odoo envoie push + SMS responsable principal | ntfy + SMS |   
| 4 — Escalade N2 | t + 10 min | Sans acquittement → SMS responsable secondaire | SMS |   
| 5 — Appel vocal | t + 20 min | Sans acquittement → appel automatique | Twilio Voice |   
| 6 — Acquittement | Variable | Responsable confirme · non-conformité Odoo créée | Odoo Qualité |   
   
   
**Fallback vNode (si Odoo injoignable) :**  
- vNode détecte l'échec API Odoo (timeout < 10s)  
- Envoi direct push ntfy + SMS sans passer par Odoo  
- Mesures bufferisées en SQLite  
- Sync automatique dès retour Odoo (non-conformité créée rétroactivement)  
**6.3 Canaux de notification**  
| | | | |  
|-|-|-|-|  
| **Canal** | **Provider** | **Coût** | **Usage** |   
| Push mobile | ntfy.sh (auto-hébergé sur VPS) | Gratuit | Alerte principale |   
| SMS | API Free Mobile (si abonné) | Gratuit | Redondance alertes |   
| SMS | OVH SMS / Twilio SMS | ~0.05€/SMS | Alternative SMS |   
| Appel vocal | **Twilio Voice** ou  **OVH Voice** | ~0.02€/appel | Escalade finale |   
   
***ntfy.sh*** * s'installe comme un container Docker supplémentaire sur le VPS Odoo.*  
 *  
 L'app ntfy (iOS/Android) permet l'acquittement d'un tap depuis la notification.*  
** **  
**6.4 Appels vocaux automatiques — Twilio Voice vs OVH Voice**  
Deux providers supportés pour les appels d'escalade. Le choix dépend des exigences du client.  
***Option A — Twilio Voice (recommandé POC)***  
| | |  
|-|-|  
| **Caractéristique** | **Détail** |   
| Déploiement | Webhook TwiML hébergé sur VPS Odoo |   
| POC | Essai gratuit ~15€ de crédit — suffisant |   
| Coût production | ~0.013€/min + 0.009€ connexion ≈ **0.02€/appel 45s** |   
| Voix FR | Amazon Polly Polly.Lea (voix française naturelle) |   
| Acquittement | Touche 1 (DTMF) → webhook /haccp/ack-call → arrêt escalade |   
| Hébergement données | Serveurs USA/UE selon région Twilio choisie |   
| Documentation | Très complète, SDK Python disponible |   
   
<!-- TwiML — Script appel HACCP -->  
 <Response>  
   <Say language="fr-FR" voice="Polly.Lea">  
     Alerte HACCP urgente. Frigo numéro 1 dépasse le seuil depuis 20 minutes.  
     Appuyez sur 1 pour confirmer votre prise en charge.  
   </Say>  
   <Gather numDigits="1" action="/haccp/ack-call" timeout="10">  
     <Say language="fr-FR" voice="Polly.Lea">  
       Appuyez sur 1, ou restez en ligne pour déclencher l'escalade.  
     </Say>  
   </Gather>  
   <Say language="fr-FR" voice="Polly.Lea">  
     Pas de réponse. Le responsable suivant va être contacté.  
   </Say>  
 </Response>  
   
***Option B — OVH Voice (clients RGPD strict)***  
| | |  
|-|-|  
| **Caractéristique** | **Détail** |   
| Déploiement | API OVH Télécom + webhook SIP/HTTP |   
| Coût production | ~0.012€/min appels France |   
| Hébergement données | 100% France (OVH Roubaix/Strasbourg) |   
| RGPD | Données d'appel en France — avantage clients secteur santé/alimentaire |   
| Voix FR | TTS OVH (qualité inférieure à Polly.Lea) |   
| Documentation | Moins complète que Twilio |   
   
***Recommandation :*** * Twilio pour le POC (setup rapide, essai gratuit, meilleure DX).*  
 *  
 OVH Voice pour les clients exigeant une souveraineté des données 100% française.*  
**6.5 Seuils HACCP configurés (v1)**  
| | | | |  
|-|-|-|-|  
| **Zone** | **Mesure** | **Seuil alerte** | **Seuil critique** |   
| Frigo positif | Température | > 4°C | > 8°C |   
| Congélateur | Température | > −15°C | > −10°C |   
| Stockage sec | Humidité relative | > 75% HR | > 80% HR |   
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsSeYxZw/lVeDGMACBrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA6fOBdd+dKAKAAAAAElFTkSuQmCC)  
**7. Intégration Odoo**  
**7.1 Déploiement Odoo**  
- **Type :** Auto-hébergé (on-premise cloud) sur VPS  
- **Provider VPS recommandé :** Hetzner CX21 (~5€/mois) ou OVH VPS SSD  
- **Version Odoo :** Community  **19** (CE) pour le POC · voir analyse CE/EE ci-dessous  
- **Stack VPS :** Docker Compose (Odoo + PostgreSQL + ntfy.sh + Chirpstack en production)  
**7.2 Choix d'édition — CE vs EE (analyse v2)**  
| | | |  
|-|-|-|  
| **Critère** | **Community Edition (CE)** | **Enterprise Edition (EE)** |   
| Licence | Gratuit | ~24€/utilisateur/mois |   
| Module Qualité (Mesure, QCP, alertes) | ✅ Inclus | ✅ Inclus |   
| Dashboard temps réel (courbes température) | ❌ Dev custom ~1 jour | ✅ Natif (Dashboards EE, 0 dev) |   
| Déclencheur IoT natif (iot.device → QCP) | ❌ Non disponible | ⚠️ Disponible mais limité aux IoT Box Odoo |   
| Dev total estimé pour HACCP complet | ~3 jours | ~1.5 jours (bridge iot.device) |   
| Break-even (2 users) | — | ~1 an de licence (576€ ≈ 1.5j dev) |   
   
**Contrainte EE IoT :** le déclencheur IoT natif EE fonctionne uniquement avec des Odoo IoT Box  
   
 (hardware Raspberry Pi Odoo). vNode n'est pas une IoT Box. En EE, deux options :  
- Continuer avec JSON-RPC direct (même qu'en CE, zéro dev supplémentaire)  
- Bridge iot.device via module custom (~1.5 jours) pour intégration native EE  
**Recommandation :**  
- **POC → CE** : zéro coût licence, démonstration complète possible via JSON-RPC direct  
- **Production → EE** si le client utilise d'autres modules Odoo (CRM, Ventes, Compta) ;  
 **CE + custom** sinon (plus économique sur la durée)  
** **  
**7.3 Stratégie module Qualité — Approche hybride retenue**  
***POC (CE ou EE) — Création directe via JSON-RPC · Zéro dev Odoo***  
vNode appelle l'API Odoo à chaque mesure pour créer un quality.check de type "Mesure",  
   
 lié à un QCP préconfiguré manuellement dans Odoo pour chaque zone/capteur.  
   
 En cas de dépassement de seuil, vNode crée un quality.alert automatiquement.  
| | | |  
|-|-|-|  
| **Composant** | **Approche POC** | **Effort** |   
| Enregistrements mesures (quality.check) | vNode → JSON-RPC direct | Zéro dev |   
| Alertes non-conformités (quality.alert) | vNode → JSON-RPC direct | Zéro dev |   
| Actions correctives | Module natif Odoo | Zéro dev |   
| Export PDF HACCP | Module natif Odoo | Zéro dev |   
   
***Production CE — Module custom *** *haccp_iot* *** (~3 jours)***  
1. **Déclencheur IoT** : endpoint dédié pour recevoir les mesures vNode et créer automatiquement  
   
 les quality.check sans configuration manuelle par zone  
2. **Dashboard HACCP** : vue graphique courbes température/temps avec seuils visualisés (~1 jour)  
***Production EE — Module bridge *** *iot.device* *** (~1.5 jours) + Dashboard natif***  
1. **Bridge vNode → iot.device** : enregistre vNode comme device virtuel Odoo, utilise  
   
 le mécanisme natif EE de déclenchement QCP (~1.5 jours)  
2. **Dashboard** : natif via Dashboards EE (line charts, granularité temporelle, zéro dev)  
**7.4 Fonctionnalités Odoo Qualité disponibles nativement**  
| | |  
|-|-|  
| **Fonctionnalité** | **Description** |   
| Points de contrôle (QCP) | Définition des zones surveillées, seuils, fréquences |   
| Contrôles de type "Mesure" | Valeur enregistrée + tolérance min/max = Pass/Fail automatique |   
| Non-conformités (quality.alert) | Création automatique par vNode sur dépassement seuil |   
| Actions correctives | Assignation à un responsable · suivi jusqu'à clôture |   
| Export PDF | Rapports HACCP réglementaires pour audits |   
| Traçabilité | Horodatage de chaque mesure, alerte et action corrective |   
   
** **  
**7.5 API vNode → Odoo**  
- **Protocole :** JSON-RPC 2.0 over HTTPS (module REST API Client de vNode)  
- **Authentification :** API key Odoo (module auth_api_key)  
- **Modèles ORM utilisés :**  
- quality.point — configuration des points de contrôle HACCP (lecture)  
- quality.check — enregistrement de chaque mesure capteur (écriture)  
- quality.alert — création de non-conformité sur dépassement seuil (écriture)  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSPBCj7fFjsymJHAjAU2QtIq6DIzW7UHAMBfnGt1V8fXEwAAXrsexNkF4H1/HJoAAAAASUVORK5CYII=)  
** **  
**8. Budget POC**  
**8.1 Matériel**  
| | | | |  
|-|-|-|-|  
| **Composant** | **Quantité** | **Prix unitaire** | **Total** |   
| Dragino LHT65 | 3 | ~40€ | ~120€ |   
| RAK7268 Gateway | 1 | ~120€ | ~120€ |   
| Ubiquiti Dream Machine SE | 1 | ~475€ | ~475€ |   
| OPS121S (déjà disponible) | 1 | — | 0€ |   
| Câbles RJ45, alimentation | — | — | ~20€ |   
| **Total matériel** |   |   | **~735€** |   
   
*Le Dream Machine SE est un investissement structurant pour l'infrastructure réseau complète* * * *du restaurant (Wi-Fi, firewall, switch PoE), pas uniquement pour ce projet HACCP.*  
**8.2 Licences logicielles**  
| | | |  
|-|-|-|  
| **Logiciel** | **POC** | **Production** |   
| vNode MQTT Client (Remote Tag) | **0€** — redémarrage toutes les 2h (mode démo) | ~1 375 – 1 595 € (one-time) |   
| vNode REST API Client (Remote Tag) | **0€** — redémarrage toutes les 2h (mode démo) | ~1 375 – 1 595 € (one-time) |   
| Odoo Community 19 (CE) | Gratuit | Gratuit |   
| Odoo Enterprise 19 (EE) | Non requis POC | ~24€/user/mois |   
| Module custom Odoo (option CE) | Non requis POC | ~3 jours de dev |   
| Module bridge iot.device (option EE) | Non requis POC | ~1.5 jours de dev |   
| **Total licences vNode POC** | **0€** | **~2 750 – 3 200 €** |   
   
*Des remises volume disponibles sur vNode à partir de 10 tags (−10% pour 10–24 unités).*  
 *  
 Confirmer avec Vester la compatibilité licence Docker (MAC address fixe) avant achat production.*  
** **  
**8.3 Coûts récurrents (mensuel)**  
| | | |  
|-|-|-|  
| **Service** | **Provider** | **Coût/mois** |   
| VPS Odoo | Hetzner CX21 | ~5€ |   
| LoRaWAN Network Server | TTN (POC) / Chirpstack (prod) | Gratuit |   
| Odoo Community | — | Gratuit |   
| ntfy.sh (auto-hébergé) | Sur VPS Odoo | Inclus |   
| SMS d'alerte | Free Mobile API ou OVH SMS | ~1–2€ |   
| **Total mensuel** |   | **~6–7€** |   
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSPBCj5fFys2mJHAjAU2QtIq6DIzW7UHAMBfnGt1V8fXEwAAXrsezp4F4CP8yfUAAAAASUVORK5CYII=)  
** **  
**9. Phases de déploiement**  
**Phase 1 — POC Démonstration (2–3 semaines)**  
- Installation Ubuntu 20.04 LTS sur OPS121S  
- Déploiement stack Docker (vNode + Mosquitto + InfluxDB + Portainer)  
- Configuration Dream Machine SE · VLANs IoT/Wi-Fi/Management · dual WAN  
- Installation et configuration RAK7268 Gateway  
- Enregistrement des 3× LHT65 sur TTN  
- Configuration vNode : ingestion MQTT TTN · règles seuils HACCP  
- Déploiement Odoo Community sur VPS · Module Qualité  
- Intégration vNode → Odoo (JSON-RPC)  
- Déploiement ntfy.sh sur VPS · configuration alertes  
- Tests bout en bout : mesure → alerte → non-conformité Odoo → rapport PDF  
**Phase 2 — Enrichissement capteurs (+ 1 semaine)**  
- Ajout capteur température chaud (bain-marie / armoire chauffante)  
- Ajout capteur ouverture porte chambre froide (optionnel)  
- Affinage des seuils et règles HACCP  
**Phase 3 — Production client**  
- Migration Ubuntu 20.04 → 22.04 LTS  
- Migration TTN → Chirpstack (Docker sur VPS Odoo)  
- Acquisition licences vNode (MQTT Client + REST API Client) — ~2 750 – 3 200 €  
- Développement module custom Odoo haccp_iot (~3 jours) : endpoint récepteur + dashboard  
- Sécurisation avancée (certificats TLS propres, accès SSH restreint)  
- Documentation utilisateur et procédures d'astreinte  
- Formation du responsable restaurant  
**Phase 4 — Extension multi-sites**  
- Architecture vNode par site (1 OPS121S par restaurant)  
- Odoo Multi-company ou instances séparées  
- Dashboard consolidé multi-sites  
- Chirpstack multi-gateway  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OQQmAABRAsSd4NIGhrOTvaQBrWMGbCFuCLTOzV2cAAPzFvVZbdXw9AQDgtesBhYQEO+64Y8AAAAAASUVORK5CYII=)  
** **  
**10. Questions ouvertes**  
| | | | | |  
|-|-|-|-|-|  
| **#** | **Question** | **Impact** | **Priorité** | **Statut** |   
| 1 | ~~Version exacte de vNode Automation et modèle de licence~~ | Architecture logicielle | Haute | ✅ Résolu v2 |   
| 2 | ~~Module Odoo Qualité HACCP : natif ou développement custom ?~~ | Charge de développement | Haute | ✅ Résolu v2 |   
| 3 | ~~Intégration Twilio Voice pour appels automatiques~~ | Alertes escalade | Moyenne | ✅ Résolu v4 |   
| 4 | ~~Stratégie de backup des données locales OPS121S → VPS~~ | Résilience données | Moyenne | ✅ Résolu v4 |   
| 5 | ~~SIM IoT M2M pour WAN 2 Dream Machine : quel opérateur ?~~ | Coût récurrent | Faible | ✅ Résolu v5 |   
| 6 | ~~Chirpstack : déploiement sur VPS Odoo ou OPS121S local ?~~ | Architecture production | Faible | ✅ Résolu v5 |   
   
**Q1 — Résolution vNode Automation (2026-05-18)**  
- **Éditeur :** Vester Business S.L. — [vnodeautomation.com](https://vnodeautomation.com "https://vnodeautomation.com")  
- **Déploiement :** Docker (MAC address fixe) sur OPS121S Ubuntu 20.04  
- **Modules requis :** MQTT Client + REST API Client (2 Remote Tag licences)  
- **Pas de module LoRaWAN natif** — TTN fait la passerelle LoRaWAN→MQTT (architecture inchangée)  
- **POC :** 0€ — mode démo, redémarrage toutes les 2h ·  **Production :** ~2 750 – 3 200 € one-time  
- **À confirmer avec Vester :** compatibilité licence en environnement Docker (MAC fixe)  
**Q2 — Résolution Module Odoo Qualité (2026-05-18)**  
- **Version Odoo retenue :** Community 19 (CE) pour le POC · CE/EE à décider avec le client final  
- **Limitation identifiée :** les QCP natifs ne supportent pas de déclencheur IoT/API externe  
- **POC :** module natif Qualité + création directe quality.check / quality.alert via JSON-RPC — zéro dev  
- **Production CE :** module custom haccp_iot (~3 jours) — déclencheur IoT + dashboard graphique  
- **Production EE :** bridge iot.device (~1.5 jours) + dashboard natif Odoo 19 (0 dev)  
** **  
**Q5 — Résolution SIM M2M WAN2 Dream Machine SE (2026-05-18)**  
**Principe :** la SIM M2M alimente le WAN2 du Dream Machine SE en failover automatique.  
   
 Consommation très faible — uniquement active quand la fibre ISP est indisponible.  
**Recommandation : 1NCE** pour le POC et la production mono-site.  
| | | | | |  
|-|-|-|-|-|  
| **Opérateur** | **Offre** | **Coût** | **Réseau** | **Recommandé** |   
| **1NCE** | 500 MB / 10 ans (roaming EU) | **10€ one-time** | Multi-opérateurs EU | ✅ POC + prod |   
| Bouygues Entreprises M2M | Forfait M2M 100 MB/mois | ~5–8€/mois | Bouygues FR | Production intensive |   
| Orange Business M2M | Forfait IoT flexible | ~5–10€/mois | Orange FR | Production intensive |   
| Free Mobile M2M | Forfait data IoT | ~2–5€/mois | Free FR | Budget |   
   
**1NCE** est particulièrement adapté au failover :  
- Tarif unique 10€ pour 10 ans — coût marginal pour un usage exceptionnel (failover rare)  
- Roaming multi-opérateurs UE — bascule automatique sur le meilleur réseau disponible  
- Compatible avec le slot SIM du Dream Machine SE (nano-SIM standard)  
- Portail de gestion IoT inclus (monitoring consommation data)  
***Configuration Dream Machine SE :*** * WAN2 via USB 4G modem ou module SIM intégré selon* * * *la version du Dream Machine SE. Vérifier la compatibilité APN 1NCE avec Ubiquiti UniFi OS.*  
** **  
**Q6 — Résolution Chirpstack (2026-05-18)**  
**Qu'est-ce que Chirpstack ?** C'est le LoRaWAN Network Server (LNS) open source qui remplace  
   
 TTN en production. Il reçoit les paquets radio de la gateway RAK7268, les déchiffre, décode  
   
 les payloads Dragino et les pousse vers vNode via MQTT — exactement le rôle de TTN, mais  
   
 auto-hébergé sur notre infrastructure.  
POC        : Gateway → TTN cloud (gratuit, zéro install) → MQTT → vNode  
 Production : Gateway → Chirpstack (notre VPS) → MQTT → vNode  
   
**Pourquoi migrer de TTN vers Chirpstack en production :**  
| | | |  
|-|-|-|  
| **Critère** | **TTN** | **Chirpstack** |   
| Données | Serveurs TTN (UE) | 100% sur votre VPS |   
| Limite messages | 30s uplink/jour/device (fair use) | Aucune limite |   
| Dépendance externe | Oui (service tiers) | Non |   
| Installation | Zéro | Docker (~30 min) |   
   
   
**Décision Q6 : Chirpstack sur le VPS Odoo** (recommandé)  
- Un seul Chirpstack gère toutes les gateways (mono et multi-sites)  
- Gestion centralisée depuis le VPS — pas de maintenance par restaurant  
- Le Dream Machine SE dual WAN garantit la connectivité gateway → VPS  
- Container Docker supplémentaire sur le VPS Odoo (RAM : ~256 MB)  
***Cas multi-sites :*** * chaque gateway de chaque restaurant pointe vers le même Chirpstack* * * *centralisé sur le VPS. Séparation des tenants par * *application* * Chirpstack.*  
** **  
**Q3 — Résolution Twilio Voice (2026-05-18)**  
**Provider retenu : Twilio** (alternative : OVH Voice pour clients RGPD strict)  
- **Déploiement :** compte Twilio + numéro dédié (~1€/mois) + webhook TwiML sur VPS Odoo  
- **POC :** essai gratuit (~15€ crédit) — suffisant pour valider le flux d'appel  
- **Coût production :** ~0.02€ par appel de 45s (France) — négligeable  
- **Script d'appel (TwiML) :**  
- <Response>  
   <Say language="fr-FR" voice="Polly.Lea">  
     Alerte HACCP urgente. Frigo numéro 1 dépasse le seuil depuis 20 minutes.  
     Appuyez sur 1 pour confirmer votre prise en charge.  
   </Say>  
   <Gather numDigits="1" action="/haccp/ack-call" timeout="10">  
     <Say language="fr-FR" voice="Polly.Lea">  
       Appuyez sur 1, ou restez en ligne pour déclencher l'escalade.  
     </Say>  
   </Gather>  
   <Say language="fr-FR" voice="Polly.Lea">  
     Pas de réponse. Le responsable suivant va être contacté.  
   </Say>  
 </Response>  
   
- **Acquittement :** touche 1 → webhook /haccp/ack-call sur VPS → vNode arrête l'escalade + Odoo horodate  
** **  
**Q4 — Résolution Backup OPS121S → VPS (2026-05-18)**  
**Outil retenu : Restic** (chiffrement AES-256, déduplication, multi-backend SFTP)  
**Données à sauvegarder et fréquence :**  
| | | | |  
|-|-|-|-|  
| **Données** | **Source** | **Fréquence** | **Rétention** |   
| InfluxDB (mesures time-series) | /var/lib/influxdb via influx backup | 1×/jour | 30j · 52 sem · 36 mois |   
| SQLite vNode (buffer offline) | /opt/vnode/data/buffer.db | 1×/15 min | 24h |   
| Config vNode (règles, seuils) | /opt/vnode/config | 1×/semaine + à chaque modif | 12 mois |   
| docker-compose + configs | /opt/docker | 1×/semaine | 12 mois |   
   
***Conformité HACCP (3 ans) :*** * les enregistrements réglementaires primaires résident dans* *** *** ***PostgreSQL Odoo sur le VPS*** * (sauvegardé via * *pg_dump* * quotidien). InfluxDB sur OPS121S* * * *est l'historique local secondaire. La rétention 36 mois sur InfluxDB est une précaution* * * *supplémentaire, non le seul support de conformité.*  
**Commandes cron OPS121S (résumé) :**  
# Quotidien — InfluxDB  
 influx backup /tmp/influx-backup && \  
 restic -r sftp:backup@vps:/backups/ops121s backup /tmp/influx-backup && \  
 restic forget --keep-daily 30 --keep-weekly 52 --keep-monthly 36 --prune  
   
 # Toutes les 15 min — SQLite buffer  
 sqlite3 /opt/vnode/data/buffer.db ".backup /tmp/vnode-buffer.db" && \  
 restic -r sftp:backup@vps:/backups/ops121s backup /tmp/vnode-buffer.db  
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OQQmAABRAsSd4EKxgBjP+Asa0hxW8ibAl2DIzR3UFAMBf3Gu1VefXEwAAXtsfSqwDVbgKngwAAAAASUVORK5CYII=)  
** **  
**11. Références matérielles**  
| | | |  
|-|-|-|  
| **Composant** | **Référence** | **Documentation** |   
| Capteur | Dragino LHT65 | dragino.com/products/lorawan-nb-iot-lorawan/lht65.html |   
| Gateway | RAK7268 WisGate Edge Lite 2 | docs.rakwireless.com |   
| Routeur | Ubiquiti Dream Machine SE | store.ui.com |   
| LNS Cloud | The Things Network | thethingsnetwork.org |   
| LNS Local | Chirpstack v4 | chirpstack.io |   
| Middleware | vNode Automation (Vester) | vnodeautomation.com |   
| Backend | Odoo Community 19 | odoo.com |   
| Notifications push | ntfy.sh | ntfy.sh |   
| SMS | Free Mobile API / OVH SMS | — |   
| Appels vocaux | Twilio Voice | twilio.com |   
| Backup | Restic | restic.net |   
   
