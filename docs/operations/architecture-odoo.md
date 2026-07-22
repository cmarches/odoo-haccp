# Architecture actuelle — Serveur Odoo

> Suite de `architecture-ops121s-vnode.md`. Ce document décrit l'état réel du serveur Odoo qui héberge le POC HACCP : instances disponibles, module custom `haccp_report` (+ variante CE), sécurité, déploiement.

## 1. Serveur

| Paramètre | Valeur |
|---|---|
| Hostname | ubuntuserver24odoo |
| IP | **192.168.1.182** |
| OS | Ubuntu 24.04 LTS |
| Accès | `ssh christian@192.168.1.182` |

**Correction par rapport à `docs/operations/vps-odoo-setup.md`** : ce fichier affirme que les instances Odoo sont "installées en natif ... pas Docker". C'est faux dans l'état actuel — `scripts/deploy-haccp-report.sh` pilote les instances via `docker exec $CONTAINER odoo ...` (conteneur `odoo19e_app`, base Postgres accédée via l'hôte `db19e`). Les 4 instances tournent en conteneurs Docker, probablement un par version/édition.

### Cartographie des instances

| Port | Instance | Version | Base de données | Conteneur (constaté) |
|---|---|---|---|---|
| 8018 | Odoo 18 CE | 18.0 | odoo18_dev (à confirmer) | — |
| 8019 | Odoo 19 CE | 19.0-20260421 | odoo19_dev | — |
| 8028 | Odoo 18 EE | 18.0+e | odoo18e_dev (à confirmer) | — |
| **8029** | **Odoo 19 EE** | 19.0+e-20260421 | **odoo19e_dev** | **`odoo19e_app`** (db : `db19e`) |

Ports 8218 / 8228 : Adminer (admin PostgreSQL via navigateur).

**Instance cible du POC HACCP : Odoo 19 EE, port 8029, base `odoo19e_dev`.**

| Paramètre | Valeur |
|---|---|
| URL | `http://192.168.1.182:8029` |
| Login admin | `cmarchesseau@aifluencedigital.com` (UID 2) |
| API Key | dans `.env` local, jamais commitée |

## 2. Module `quality_control` (Enterprise)

Module Odoo EE standard, installé sur `odoo19e_dev`. Sert de socle : `quality.check`, `quality.alert`, `quality.point` (QCP).

### QCPs HACCP créés

| ID | Nom | Tolérance | Unité |
|---|---|---|---|
| #1 | Frigo Positif — Surveillance HACCP | -30 → **4** | °C |
| #2 | Congélateur — Surveillance HACCP | -40 → **-15** | °C |
| #3 | Stockage Sec — Humidité HACCP | 0 → **75** | % |

Ces `qcp_id` sont ceux référencés côté vNode dans `RestApiClient-config.n3c` (voir `architecture-ops121s-vnode.md` §3.2). `measure_success` (pass/fail) est calculé automatiquement par Odoo à la création du `quality.check` ; `quality_state` doit être écrit explicitement par l'appelant.

Procédure complète (création QCP, appels XML-RPC, tests) : `docs/operations/odoo-qualite-qcp.md`.

## 3. Modules custom AIFluence Digital

Deux modules dans `odoo-addons/`, développés pour ce POC.

### 3.1 `haccp_report` (édition Enterprise)

`depends: quality_control, web, mail, portal`. Module applicatif principal, plusieurs fonctionnalités sous le menu **"Méthode HACCP"** (renommé depuis "Rapports HACCP") :

**a) Rapport PDF réglementaire DDPP** (`haccp.report`, `mail.thread`)
- Modèle avec période (`date_start`/`date_end`), responsable, société, état (brouillon/généré).
- Action serveur ajoutée sur la liste `quality.check` : bouton "Rapport HACCP DDPP" qui pré-remplit un nouveau rapport sur le mois en cours (`views/quality_inherit.xml`).
- Génération PDF via `models/report_renderer.py` + `report/report_template.xml`.

**b) 5 calculateurs HACCP** (menu "Calculs et formules", tous `TransientModel`)
| Modèle | Rôle |
|---|---|
| `haccp.dlc` | DLC/DLUO par famille de produit × condition de conservation (table `haccp_dlc_table.py`) |
| `haccp.refroidissement` | Fenêtre réglementaire de refroidissement +63°C → +10°C en 2h |
| `haccp.dilution` | Ratios produit/eau, 1:10 à 1:100 + valeur custom |
| `haccp.decongelation` | Durée de décongélation + calcul de DLC secondaire |
| `haccp.reassort` | Point de commande = consommation × délai + stock de sécurité |

**c) Bibliothèque de documents** (menu "Bibliothèque de documents", `haccp.document`, modèle permanent)
- Synchronise depuis un `manifest.json` distant (name/category/url/hash MD5 par document) : compare le hash local au distant, télécharge si différent, stocke en `ir.attachment`.
- 4 catégories : releves / affiches / reglementation / fiches_pratiques.
- `MANIFEST_URL` pointe aujourd'hui sur le serveur Odoo local (`http://192.168.1.182:8029/haccp_report/static/haccp/manifest.json`), en attendant l'hébergement définitif sur `aifluencedigital.com` — **à changer avant tout déploiement client**.
- 18 PDF brandés AIFluence Digital déjà présents dans `haccp_report/static/haccp/`.
- Bouton "Mettre à jour les documents" restreint à `quality.group_quality_manager`.

**d) Étiquettes DLC — portail cuisine** (fonctionnalité la plus récente, mergée le 2026-07-20, commit `4a97030`)

Flux : un utilisateur du groupe portail dédié imprime une étiquette DLC secondaire depuis son téléphone/tablette, sur l'imprimante Zebra de la cuisine, et un QR code sur l'étiquette permet de clôturer le suivi plus tard.

- Modèle `haccp.dlc.ouverture` (`portal.mixin`, `mail.thread`) : produit, famille, condition, date d'ouverture, opérateur, `duree_jours`/`date_limite` calculés depuis `DLC_TABLE`, statut (`ouvert`/`termine`/`jete`), `access_token` (portail).
- Contrôleur `controllers/haccp_portal.py` :
  - `GET/POST /haccp/etiquette/nouvelle` (`auth='user'`, réservé groupe cuisine) — formulaire de saisie puis impression.
  - `POST /haccp/etiquette/<id>/<token>/reessayer` — relance l'impression si échec imprimante.
  - `GET /haccp/etiquette/<id>/<token>` (`auth='public'`) — fiche publique accessible par scan QR, sans compte pour la simple consultation.
  - `POST /haccp/etiquette/<id>/<token>/cloturer` (`auth='user'`, groupe cuisine) — clôture avec statut terminé/jeté.
- Impression : `models/zpl_printer.py::build_zpl()` génère du ZPL envoyé en TCP brut au port 9100 de l'imprimante (`send_zpl()`), IP configurée via `ir.config_parameter` `haccp_report.zebra_printer_ip`.
  - Gabarit calibré sur du matériel réel (OXHOO TLP200, étiquette 99×80mm, 203dpi → `^PW792 ^LL640`), encodage UTF-8 déclaré (`^CI28`), code-barre + QR côte à côte.
  - **Spécifique au format 99×80mm** : recalculer `^PW`/`^LL` et repositionner le contenu pour toute autre taille d'étiquette/imprimante.
- Sécurité : groupe `haccp_report.group_haccp_kitchen` (implique `base.group_portal`), **aucun droit ACL direct** sur `haccp.dlc.ouverture` en écriture pour ce groupe — tout passe par le contrôleur en `sudo()`, qui vérifie le groupe explicitement (`_check_kitchen_group()`). La page de clôture n'est volontairement pas dans un menu — accessible uniquement via le lien du QR imprimé.
- Point d'entrée découvrable : carte sur `/my` (portail), visible uniquement pour `group_haccp_kitchen` (template `portal.portal_my_home` étendu).
- Compte de démo cuisine : `cuisine@aifluencedigital.com` — voir mémoire `project-etiquettes-dlc-implementation` pour le mot de passe et le détail des 3 bugs matériels corrigés.

### 3.2 `haccp_report_ce` (variante Community, OCA)

`depends: haccp_report, quality_control_oca, web, mail`. Réexpose les mêmes modèles (`haccp.report`, `haccp.dlc`, etc.) avec des ACL pointant vers les groupes OCA (`quality_control.group_quality_user/manager` au lieu de `quality.group_quality_*`) et rattache le menu racine au menu qualité OCA (`views/menu_override.xml`).

⚠️ Commentaire dans le manifeste : *"groupes OCA présumés depuis branche 18.0 — à vérifier sur 19.0"* — pas encore validé sur Odoo 19 CE/OCA en conditions réelles, contrairement à `haccp_report` (EE) qui est validé de bout en bout.

## 4. Déploiement

Script `scripts/deploy-haccp-report.sh [--install|--update|--test]` :
1. `rsync` le module local vers `christian@192.168.1.182:/home/christian/odoo-multiversion/v19e/addons/haccp_report/`.
2. Exécute `docker exec odoo19e_app odoo -d odoo19e_dev ... -u haccp_report --stop-after-init` (ou `-i` en install, `--test-enable -u` en test) sur un port alternatif 8099 pour ne pas percuter le serveur principal.

**Piège connu** (mémoire `feedback-deploy-restart`) : `--stop-after-init` met à jour la base puis s'arrête — le serveur principal continue de tourner avec l'ancien code Python en mémoire. Si des fichiers `models/` ont changé, il faut enchaîner :
```bash
./scripts/deploy-haccp-report.sh --update
ssh christian@192.168.1.182 "docker restart odoo19e_app"
```
Un changement XML/CSV seul (vues, données) ne nécessite pas de restart.

Reprise du développement en local : voir mémoire `project-local-setup` (vérifier le commit local, `git pull` si besoin, puis `--update` + `--test`).

## 5. Intégration avec vNode

Le lien avec le serveur OPS121S se fait uniquement via XML-RPC HTTPS/HTTP interne LAN, initié par `haccp-odoo-bridge.service` (voir `architecture-ops121s-vnode.md` §4) :
```
vNode RestApiClient → bridge.py (192.168.1.101:5001) → XML-RPC → Odoo 19 EE (192.168.1.182:8029)
```
Odoo ne fait aucun appel sortant vers vNode — toute la logique d'ingestion IoT → qualité est côté bridge.

## Écarts avec la documentation existante

| Aspect | Doc existant (`vps-odoo-setup.md`) | État réel constaté |
|---|---|---|
| Mode d'installation Odoo | "En natif, pas Docker" | Conteneurs Docker (`odoo19e_app` + `db19e` au moins pour l'instance 19 EE) |
| Groupes ACL `haccp_report_ce` | Non documenté ailleurs | Présumés depuis la branche OCA 18.0, non vérifiés sur 19.0 |
| Hébergement bibliothèque documents | Cible `aifluencedigital.com/haccp/manifest.json` | Sert actuellement depuis le module local (mode lowcode, pas encore d'accès au site) |
