# Design — Méthode HACCP : Calculs, formules et bibliothèque de documents

**Date :** 2026-05-23
**Module :** `haccp_report` (extension)
**Statut :** Approuvé

---

## Contexte

Extension du module `haccp_report` avec deux nouvelles fonctionnalités :

1. **5 calculateurs HACCP ponctuels** sous "Calculs et formules" — outils à usage immédiat, sans persistance
2. **Bibliothèque de documents HACCP** sous "Bibliothèque de documents" — PDFs aux couleurs AIFluence Digital, synchronisés depuis le site aifluencedigital.com

Le menu racine "Rapports HACCP" est renommé en **"Méthode HACCP"** pour englober rapports, outils et documents.

---

## Structure des menus

```
Qualité
  └── Méthode HACCP                    ← renommé (était "Rapports HACCP")
        ├── Rapports HACCP DDPP        ← inchangé (sequence 10)
        ├── Calculs et formules        ← nouveau (sequence 20)
        │     ├── DLC / DLUO          (sequence 10)
        │     ├── Refroidissement     (sequence 20)
        │     ├── Dilution            (sequence 30)
        │     ├── Décongélation       (sequence 40)
        │     └── Réassort            (sequence 50)
        └── Bibliothèque de documents  ← nouveau (sequence 30)
```

---

## PARTIE 1 — Calculs et formules

### Architecture technique

**Pattern :** 5 `TransientModel` Odoo. Champs de résultat = champs calculés non stockés (`compute=` + `@api.depends`). Recalcul automatique à chaque saisie, sans bouton "Calculer". Aucune table persistante créée. Chaque calculateur s'ouvre en **popup dialog** (`target='new'`).

**Fichiers :**

```
haccp_report/
├── models/
│   ├── __init__.py                    ← ajouter 5 imports
│   ├── haccp_dlc.py                   ← nouveau
│   ├── haccp_refroidissement.py       ← nouveau
│   ├── haccp_dilution.py              ← nouveau
│   ├── haccp_decongelation.py         ← nouveau
│   └── haccp_reassort.py              ← nouveau
├── views/
│   ├── menu.xml                       ← renommage + nouveaux menus
│   └── haccp_calculs_views.xml        ← nouveau (5 forms + 5 actions)
└── __manifest__.py                    ← ajouter haccp_calculs_views.xml
```

---

### Calculateur 1 — DLC / DLUO

**Modèle :** `haccp.dlc`

| Champ | Type | Description |
|---|---|---|
| `famille` | Selection | Viande crue, Poisson, Charcuterie, Produit laitier, Plat cuisiné, Légumes, Autre |
| `condition` | Selection | Réfrigéré (+4°C), Congelé (-18°C), Ambiant |
| `date_fabrication` | Date | Date de fabrication / ouverture |
| `duree_jours` | Integer | **Calculé** — table fixe famille × condition |
| `date_limite` | Date | **Calculé** — `date_fabrication + duree_jours` |
| `statut` | Char | **Calculé** — "✓ Valide" / "⚠ Expire bientôt (≤2j)" / "✗ Expiré" |

**Table de durées (jours) :**

| Famille | Réfrigéré | Congelé | Ambiant |
|---|---|---|---|
| Viande crue | 3 | 90 | 0 |
| Poisson | 2 | 90 | 0 |
| Charcuterie | 5 | 90 | 30 |
| Produit laitier | 7 | 30 | 0 |
| Plat cuisiné | 3 | 90 | 0 |
| Légumes | 5 | 180 | 7 |
| Autre | 3 | 90 | 7 |

> Les durées sont indicatives pour un outil de démonstration. À affiner selon la réglementation client.

---

### Calculateur 2 — Refroidissement rapide

**Modèle :** `haccp.refroidissement`

| Champ | Type | Description |
|---|---|---|
| `heure_debut` | Datetime | Heure de début du refroidissement |
| `heure_limite` | Datetime | **Calculé** — `début + 2h` (règle HACCP) |
| `heure_mi_parcours` | Datetime | **Calculé** — `début + 1h` (objectif : ≤21°C à mi-parcours) |
| `statut` | Char | **Calculé** — "⏳ EN COURS" si `now() < heure_limite`, sinon "✗ FENÊTRE DÉPASSÉE" |

**Règle appliquée :** +63°C → +10°C en moins de 2 heures (règle HACCP standard).

> Le statut indique si la fenêtre de 2h est encore ouverte. Il ne confirme pas l'atteinte des +10°C (mesure physique hors scope). Statut calculé à l'ouverture — l'utilisateur rouvre le wizard si besoin.

---

### Calculateur 3 — Dilution produit nettoyant

**Modèle :** `haccp.dilution`

| Champ | Type | Description |
|---|---|---|
| `volume_total` | Float | Volume total souhaité (litres) |
| `ratio` | Selection | 1:10 / 1:20 / 1:50 / 1:100 / Personnalisé |
| `ratio_custom` | Integer | Visible uniquement si ratio = Personnalisé |
| `volume_produit_ml` | Float | **Calculé** — `(volume_total × 1000) / (ratio_effectif + 1)` |
| `volume_eau_l` | Float | **Calculé** — `volume_total - (volume_produit_ml / 1000)` |

**Formule :** Pour un ratio 1:N, `volume_produit = volume_total / (N + 1)`.

`ratio_effectif` = valeur numérique du ratio sélectionné (10, 20, 50, 100) ou `ratio_custom` si ratio = "Personnalisé".

---

### Calculateur 4 — Décongélation

**Modèle :** `haccp.decongelation`

| Champ | Type | Description |
|---|---|---|
| `famille` | Selection | Viande entière, Volaille, Poisson, Viande hachée |
| `poids_kg` | Float | Poids en kg |
| `debut_decongelation` | Datetime | Heure de mise en décongélation au réfrigérateur |
| `duree_heures` | Float | **Calculé** — table famille × poids |
| `fin_decongelation` | Datetime | **Calculé** — `début + duree_heures` |
| `dlc_secondaire` | Date | **Calculé** — `fin_decongelation.date() + 1 jour` |

**Table de durées (heures/kg) :**

| Famille | Heures par kg |
|---|---|
| Viande entière | 24 |
| Volaille | 20 |
| Poisson | 12 |
| Viande hachée | 8 |

> Durée minimale = 2h. Décongélation au réfrigérateur (+4°C) uniquement.

---

### Calculateur 5 — Point de réassort

**Modèle :** `haccp.reassort`

| Champ | Type | Description |
|---|---|---|
| `stock_actuel` | Float | Stock actuel (unités) |
| `conso_journaliere` | Float | Consommation moyenne par jour |
| `delai_livraison` | Integer | Délai fournisseur (jours) |
| `stock_securite` | Float | Stock de sécurité souhaité |
| `point_commande` | Float | **Calculé** — `conso_journaliere × delai_livraison + stock_securite` |
| `jours_restants` | Float | **Calculé** — `(stock_actuel - point_commande) / conso_journaliere` |
| `statut` | Char | **Calculé** — "✗ COMMANDER MAINTENANT" si `stock_actuel ≤ point_commande`, sinon "✓ OK" |

---

## PARTIE 2 — Bibliothèque de documents

### Concept

AIFluence Digital est la **source de vérité** pour les documents HACCP (PDFs à la charte graphique). Odoo se synchronise à la demande via un bouton réservé aux managers. Les documents sont hébergés en cache local dans Odoo après synchronisation, téléchargeables par tous les utilisateurs HACCP.

### Architecture technique

**Modèle `haccp.document`** (modèle permanent) :

| Champ | Type | Description |
|---|---|---|
| `name` | Char | Nom du document |
| `category` | Selection | releves / affiches / reglementation / fiches_pratiques |
| `description` | Text | Courte description |
| `source_url` | Char | URL du PDF sur aifluencedigital.com |
| `attachment_id` | Many2one `ir.attachment` | PDF en cache local dans Odoo |
| `date_sync` | Datetime | Dernière synchronisation réussie |
| `file_hash` | Char | Hash MD5 — détecte si le PDF a changé côté serveur |

**Statut calculé (non stocké) :**
- `✓ Téléchargé` — attachment présent (date_sync renseignée)
- `⬇ Non téléchargé` — pas d'attachment

> Le statut "mise à jour disponible" ne peut être connu qu'en fetchant le manifest. C'est le bouton sync qui détecte et applique les changements, puis affiche le rapport (X ajoutés, Y mis à jour, Z inchangés).

### Manifest JSON (hébergé sur aifluencedigital.com)

URL fixe : `https://aifluencedigital.com/haccp/manifest.json`

```json
{
  "version": "2026-05-23",
  "documents": [
    {
      "name": "Fiche températures positives",
      "category": "releves",
      "description": "Traçabilité des températures frigos 0-5°C",
      "url": "https://aifluencedigital.com/haccp/documents/fiche-temperatures-positives.pdf",
      "hash": "abc123..."
    }
  ]
}
```

### Catalogue initial (18 documents)

| Catégorie | Documents |
|---|---|
| **Relevés & traçabilité** | Fiche températures positives, Fiche températures négatives, Registre allergènes |
| **Affiches de sensibilisation** | Lavage des mains, Planches à découper, Chaîne du froid, Tenue d'hygiène, Fiche recette, Coupure électrique |
| **Réglementation** | Décret 0043 (02/2024), Règlement CE 178/2002, Règlement CE 852/2004, Cerfa 12211-02 |
| **Fiches pratiques** | METRO Hygiène n°3, METRO Hygiène n°4, METRO Hygiène n°5, METRO Plan nettoyage, METRO Plan nettoyage durable |

### Mécanisme de synchronisation

Bouton "Mettre à jour les documents" (`group_quality_manager` uniquement) :

1. Fetch `manifest.json` depuis aifluencedigital.com
2. Pour chaque entrée du manifest :
   - Si document absent dans Odoo → créer + télécharger PDF + stocker attachment
   - Si hash différent → re-télécharger PDF + mettre à jour attachment + date_sync
   - Si hash identique → ne rien faire
3. Afficher un message de résultat : "X ajoutés, Y mis à jour, Z inchangés"

### Vues

**Vue liste** (défaut) — colonnes : Nom, Catégorie, Description, Date sync, Statut (badge coloré)

**Vue kanban** — cartes groupées par catégorie, bouton "Télécharger" sur chaque carte

**Droits d'accès :**
- `group_quality_user` — lecture + téléchargement
- `group_quality_manager` — lecture + téléchargement + synchronisation

### Fichiers

```
haccp_report/
├── models/
│   ├── haccp_document.py          ← nouveau (modèle + méthode sync)
│   └── __init__.py                ← ajouter import
├── views/
│   ├── haccp_document_views.xml   ← nouveau (list + kanban + form)
│   └── menu.xml                   ← ajouter menu Bibliothèque (seq 30)
├── security/
│   └── ir.model.access.csv        ← ajouter droits haccp.document
└── __manifest__.py                ← ajouter haccp_document_views.xml
```

---

## Sécurité et accès (synthèse)

| Fonctionnalité | group_quality_user | group_quality_manager |
|---|---|---|
| Calculateurs | Accès complet | Accès complet |
| Bibliothèque — lecture/téléchargement | Oui | Oui |
| Bibliothèque — synchronisation | Non | Oui |

---

## Hors scope

- Persistance / historique des calculs
- Export PDF des résultats de calcul
- Compte à rebours live (JavaScript) pour le minuteur de refroidissement
- Paramétrage des tables de durées depuis l'interface
- Création / édition de documents depuis Odoo (source unique = aifluencedigital.com)
- Synchronisation automatique planifiée (cron)
