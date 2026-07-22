# Spec — Architectures HACCP IoT par tier d'établissement

**Date :** 2026-05-22
**Statut :** En cours de discussion — base de travail approuvée
**Auteur :** Brainstorming AIFluence Digital
**Périmètre :** Définition des 6 scénarios d'architecture de la solution HACCP IoT, du capteur au rapport PDF DDPP

> **Amendé le 2026-07-22** par `2026-07-22-architecture-sans-vnode-design.md` : la décision D3 et les Cas C, D, E sont mis à jour (vNode retiré, ChirpStack self-hosté sur l'edge remplace TTN+vNode). Cas A, B, F inchangés. Se référer au document de 2026-07-22 pour l'architecture actuelle de ces trois cas.

---

## 1. Contexte

Le POC HACCP IoT (Cas D — architecture actuelle) est validé sur Odoo 19 EE avec edge node OPS121S. L'objectif est de définir des architectures adaptées à différents profils d'établissements pour proposer une offre commerciale graduée.

**Client minimum viable identifié :** moyen resto (Cas D). Le tier petit resto artisan (budget < 30€/mois logiciel) n'est pas la cible directe avec l'offre EE actuelle.

---

## 2. Les 6 scénarios (Cas A à F)

### Cas A — CE + OCA Quality (Futur, non développé)
- **Cible :** petit resto, budget minimal
- **Odoo :** Community Edition + module OCA quality (équivalent open-source de quality_control EE)
- **LNS :** TTN cloud (gratuit)
- **Edge :** absent
- **Bridge :** bridge.py adapté pour OCA
- **Rapport :** haccp_report à réécrire sans dépendance EE
- **Coût logiciel :** ~5€/mois (VPS CX21 uniquement)
- **Blockers :** OCA quality non vérifié sur Odoo 19 · dev 3-5j requis
- **Statut :** ⚠ Non développé

### Cas B — VPS Lean · TTN Direct ⭐ Baseline recommandée
- **Cible :** petit/moyen resto sans edge node
- **Odoo :** EE sur VPS Hetzner CX21 (~5-8€/mois)
- **LNS :** TTN cloud (gratuit, webhook HTTP → bridge.py)
- **Edge :** absent (pas de fallback local)
- **Bridge :** bridge.py sur VPS — déjà développé ✓
- **Rapport :** haccp_report sur VPS — déjà développé ✓
- **Coût logiciel :** ~30-40€/mois (VPS + licence EE 1 user)
- **Matériel one-shot :** ~255€ (capteurs + gateway)
- **Point d'attention :** bridge.py à adapter pour recevoir les webhooks TTN (format JSON TTN différent du format vNode actuel)
- **Statut :** ✓ Opérationnel (adaptation bridge.py à faire)

### Cas C — VPS Full Stack (Chirpstack + vNode + Odoo EE)
- **Cible :** moyen resto souhaitant autonomie et pas de dépendance TTN
- **Odoo :** EE sur VPS Hetzner CX31 (~15€/mois, plus puissant)
- **LNS :** Chirpstack self-hosted sur VPS (remplace TTN)
- **Edge :** absent (vNode tourne sur le VPS)
- **vNode :** sur VPS — licence MAC virtuel à confirmer avec Vester
- **Mosquitto :** sur VPS
- **Bridge :** bridge.py sur VPS — déjà développé ✓
- **Coût logiciel :** ~40-55€/mois + licence vNode à confirmer
- **Blocker :** licence vNode sur VPS (MAC virtuel) à valider
- **Statut :** ✓ Opérationnel en POC (licence VPS à confirmer)

### Cas D — Moyen Resto + Edge Node (Architecture POC actuelle)
- **Cible :** moyen resto avec edge node physique sur site
- **Odoo :** EE sur VPS Hetzner CX21
- **LNS :** TTN cloud ou Chirpstack cloud
- **Edge :** Raspberry Pi 5 (~80€) ou OPS121S (~200€) sur site
- **vNode :** sur edge node (licence MAC physique — OK)
- **Bridge :** bridge.py sur edge — déjà développé et validé ✓
- **Failover :** edge node assure le fallback si VPS indisponible
- **Coût logiciel :** ~35-55€/mois
- **Matériel one-shot :** ~485-670€ (capteurs + gateway + routeur dual-WAN + edge node)
- **Statut :** ✓ Opérationnel — c'est l'architecture POC validée

### Cas E — Chaîne de Restaurants · Multi-sites
- **Cible :** groupes de restauration, franchises
- **Odoo :** EE centralisé multi-company sur VPS CX41+ (~25-30€/mois)
- **LNS :** Chirpstack auto-hébergé sur VPS central (multi-tenant)
- **Edge :** OPS121S (~200€) par restaurant
- **vNode :** 1 instance par site (licence par MAC physique)
- **InfluxDB :** Cloud central pour vision multi-sites (~20-50€/mois)
- **Coût logiciel :** ~80-150€/mois (hors licences Odoo EE par user)
- **Matériel one-shot :** ~995€/site
- **Statut :** ⚠ À adapter (multi-company Odoo + Chirpstack central)

### Cas F — Collectivité (École, Hôpital, Cantine)
- **Cible :** établissements publics ou para-publics avec DSI
- **Odoo :** on-premise sur serveur DSI ou infogéré
- **LNS :** Chirpstack on-premise (exigence données hors cloud)
- **Edge :** serveur DSI existant (mutualisé)
- **Alertes :** ntfy self-hosted si imposé par la DSI
- **Contraintes :** marchés publics, RGPD strict, validation DSI
- **Coût logiciel :** ~0-30€/mois (infra DSI mutualisée — coût = intégration)
- **Statut :** ⚠ À adapter (contraintes DSI à qualifier client par client)

---

## 3. Décisions structurantes

### D1 — Modèle de déploiement par défaut
**Décision :** 1 VPS par client (pas de mutualisé multi-tenant). AIFluence opère l'infra (modèle MSP), le client paie sa licence Odoo EE directement à Odoo SA.

### D2 — Licence Odoo EE
**Décision :** Le client paie sa licence EE. Objectif = offre la moins chère possible sur VPS auto-hébergé (~25-32€/user/mois via Odoo SA). Cas A (CE) en réserve si la demande petit artisan devient significative.

### D3 — Baseline technique
**Décision :** Cas B est la baseline opérationnelle de départ. Cas D est l'architecture de référence (POC validé). Cas C bloqué sur validation licence vNode VPS.

### D4 — InfluxDB
**Décision :** Non câblé dans les Cas A/B/C. Pertinent uniquement à partir du Cas E (vision multi-sites). À intégrer ultérieurement.

### D5 — bridge.py et TTN webhook
**Travail restant Cas B :** adapter bridge.py pour recevoir le format webhook natif TTN (JSON TTN uplink) en plus du format vNode actuel.

---

## 4. Points ouverts à résoudre

| # | Question | Bloque |
|---|----------|--------|
| 1 | Licence vNode sur VPS (MAC virtuel) — confirmer avec Vester | Cas C |
| 2 | OCA quality module compatible Odoo 19 ? | Cas A |
| 3 | Adapter bridge.py au format webhook TTN | Cas B (complet) |
| 4 | Multi-company Odoo EE : 1 DB ou N DB par chaîne ? | Cas E |
| 5 | Contraintes DSI type : liste à qualifier | Cas F |

---

## 5. Tableau de référence visuel

Tableau HTML interactif généré et sauvegardé dans :
`.superpowers/brainstorm/` — fichier `tableau-complet-v2.html`

SVG architecture POC actuelle (Cas D) : `docs/architecture-haccp-actuelle.svg`
