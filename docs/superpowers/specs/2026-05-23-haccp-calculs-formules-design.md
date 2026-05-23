# Design — Méthode HACCP : Calculs et formules

**Date :** 2026-05-23
**Module :** `haccp_report` (extension)
**Statut :** Approuvé

---

## Contexte

Ajout de 5 calculateurs HACCP ponctuels dans le menu Odoo Qualité, sous un nouveau groupe "Calculs et formules". Les outils sont inspirés de methodehaccp.com. Pas de persistance des données — outils à usage immédiat uniquement.

Le menu "Rapports HACCP" est renommé en **"Méthode HACCP"** pour englober rapports et outils.

---

## Structure des menus

```
Qualité
  └── Méthode HACCP              ← renommé (était "Rapports HACCP")
        ├── Rapports HACCP DDPP  ← inchangé (sequence 10)
        └── Calculs et formules  ← nouveau (sequence 20)
              ├── DLC / DLUO          (sequence 10)
              ├── Refroidissement     (sequence 20)
              ├── Dilution            (sequence 30)
              ├── Décongélation       (sequence 40)
              └── Réassort            (sequence 50)
```

Chaque calculateur s'ouvre en **popup dialog** (`target='new'`). Résultats calculés en temps réel via `@api.depends`.

---

## Architecture technique

**Pattern :** 5 `TransientModel` Odoo. Champs de résultat = champs calculés non stockés (`compute=` + `@api.depends`). Recalcul automatique à chaque saisie, sans bouton "Calculer". Aucune table persistante créée.

**Fichiers à créer/modifier :**

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

## Calculateur 1 — DLC / DLUO

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

## Calculateur 2 — Refroidissement rapide

**Modèle :** `haccp.refroidissement`

| Champ | Type | Description |
|---|---|---|
| `heure_debut` | Datetime | Heure de début du refroidissement |
| `heure_limite` | Datetime | **Calculé** — `début + 2h` (règle HACCP) |
| `heure_mi_parcours` | Datetime | **Calculé** — `début + 1h` (objectif : ≤21°C à mi-parcours) |
| `statut` | Char | **Calculé** — "⏳ EN COURS" si `now() < heure_limite`, sinon "✗ FENÊTRE DÉPASSÉE" |

**Règle appliquée :** +63°C → +10°C en moins de 2 heures (règle HACCP standard).

> Le statut indique si la fenêtre de 2h est encore ouverte. Il ne confirme pas l'atteinte des +10°C (mesure physique hors scope). Statut calculé à l'ouverture — pas de rafraîchissement automatique, l'utilisateur rouvre le wizard si besoin.

---

## Calculateur 3 — Dilution produit nettoyant

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

## Calculateur 4 — Décongélation

**Modèle :** `haccp.decongelation`

| Champ | Type | Description |
|---|---|---|
| `famille` | Selection | Viande entière, Volaille, Poisson, Viande hachée |
| `poids_kg` | Float | Poids en kg |
| `debut_decongelation` | Datetime | Heure de mise en décongélation au réfrigérateur |
| `duree_heures` | Float | **Calculé** — table famille × poids |
| `fin_decongelation` | Datetime | **Calculé** — `début + duree_heures` |
| `dlc_secondaire` | Date | **Calculé** — `fin_decongelation.date() + 24h` |

**Table de durées (heures/kg) :**

| Famille | Heures par kg |
|---|---|
| Viande entière | 24 |
| Volaille | 20 |
| Poisson | 12 |
| Viande hachée | 8 |

> Durée minimale = 2h. Décongélation au réfrigérateur (+4°C) uniquement.

---

## Calculateur 5 — Point de réassort

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

## Sécurité et accès

Même groupe que l'existant : `quality.group_quality_user`. Pas de règles d'accès supplémentaires (TransientModel, pas de données sensibles).

---

## Hors scope

- Persistance / historique des calculs
- Export PDF des résultats
- Compte à rebours live (JavaScript) pour le minuteur de refroidissement
- Paramétrage des tables de durées depuis l'interface
