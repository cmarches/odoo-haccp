# Design — Module HACCP dual-compatible EE + CE/OCA

**Date :** 2026-05-23  
**Auteur :** AIFluence Digital  
**Statut :** Approuvé

---

## Contexte

Le module `haccp_report` tourne actuellement sur Odoo 19 Enterprise Edition et dépend du module
`quality_control` EE. Certains prospects ciblent Odoo 19 Community Edition (CE) avec le module OCA
`quality_control_oca`. L'objectif est de supporter les deux éditions sans dupliquer la logique métier.

### Contrainte découverte

La seule dépendance véritablement EE-exclusive dans `haccp_report` est le module `quality` d'Odoo
EE, qui fournit les groupes de sécurité `quality.group_quality_user` et
`quality.group_quality_manager`. Ce module n'existe pas en CE. Tout le reste (`quality.check`,
`quality.point`, `quality.alert`, `quality_control.menu_quality_root`) est commun aux deux éditions
car OCA adopte les mêmes noms de modèles et de menus.

---

## Approche retenue — Module compagnon `haccp_report_ce`

Un module compagnon léger est créé pour CE+OCA. La logique Python reste dans `haccp_report` (source
unique de vérité). `haccp_report_ce` ne contient que des overrides XML/CSV pour adapter les
références de groupes et de menu parent à OCA.

Pour que `haccp_report_ce` puisse dépendre de `haccp_report`, ce dernier doit être installable en
CE. La modification requise est minimale : remplacer les références au groupe `quality` EE par des
groupes HACCP définis dans le module lui-même.

---

## Composants

### 1. Modification de `haccp_report` — groupes HACCP propres

**Nouveau fichier : `security/haccp_groups.xml`**

Définit deux groupes `res.groups` propres au module :

- `haccp_report.group_haccp_user` — hérite de `quality.group_quality_user` quand disponible (EE),
  sinon standalone (CE)
- `haccp_report.group_haccp_manager` — hérite de `quality.group_quality_manager` quand disponible

Ces groupes remplacent toutes les références EE dans les fichiers de sécurité et de menus. Le
module reste compatible EE car l'héritage de groupe est préservé ; il devient aussi compatible CE
car la définition du groupe ne dépend plus du module `quality`.

**Fichiers modifiés :**

| Fichier | Changement |
|---|---|
| `security/haccp_groups.xml` | Nouveau — définit `group_haccp_user` et `group_haccp_manager` |
| `security/ir.model.access.csv` | 9 lignes : `quality.group_quality_*` → `haccp_report.group_haccp_*` |
| `views/menu.xml` | 5 occurrences : `groups="quality.group_quality_user"` → `groups="haccp_report.group_haccp_user"` |
| `__manifest__.py` | Ajouter `haccp_groups.xml` dans `data`, retirer la note CE-incompatible |

Tous les autres fichiers Python, vues, rapports, calculateurs, bibliothèque de documents :
**inchangés**.

---

### 2. Nouveau module `haccp_report_ce`

Module squelette de 4 fichiers. Zéro Python.

```
odoo-addons/haccp_report_ce/
├── __init__.py
├── __manifest__.py
└── security/
│   └── ir.model.access.csv        ← groupes OCA
└── views/
    └── menu_override.xml          ← parent et groups OCA
```

**`__manifest__.py`**

```python
{
    'name': 'Rapport HACCP DDPP — Community Edition',
    'version': '19.0.1.0.0',
    'summary': 'Variante CE du module HACCP DDPP (OCA quality_control_oca)',
    'category': 'Quality',
    'author': 'AIFluence Digital',
    'depends': ['haccp_report', 'quality_control_oca', 'web', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu_override.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
```

**`security/ir.model.access.csv`**

Reprend les 9 lignes de `haccp_report/security/ir.model.access.csv` mais cible les groupes OCA :
`quality_control_oca.group_quality_user` et `quality_control_oca.group_quality_manager`.

> **Note :** les noms exacts des groupes OCA doivent être vérifiés sur la branche 19.0 du dépôt
> `OCA/quality-management` quand elle sera disponible. Valeurs présumées issues de la branche 18.0.

**`views/menu_override.xml`**

Surcharge les menus de `haccp_report` pour pointer vers le menu racine OCA et utiliser les groupes
OCA. Utilise `<menuitem>` avec les `id` qualifiés du module `haccp_report` (ex. `haccp_report.menu_haccp_reports_root`) pour surcharger le `parent` et `groups` définis dans `haccp_report/views/menu.xml`.

```xml
<menuitem
  id="haccp_report.menu_haccp_reports_root"
  parent="quality_control_oca.menu_quality_root"
  groups="quality_control_oca.group_quality_user"/>
```

---

### 3. Modification de `bridge.py` — mode OCA

**Variable d'environnement :** `ODOO_QUALITY_BACKEND=ee|oca` (défaut : `ee`)

La fonction `create_quality_check` existante est renommée `_create_quality_check_ee`. Une nouvelle
fonction `_create_quality_check_oca` est ajoutée. Un dispatcher public `create_quality_check`
délègue selon `QUALITY_BACKEND`.

**Différence EE vs OCA dans le bridge :**

| Aspect | EE | OCA |
|---|---|---|
| Calcul pass/fail | Délégué à `measure_success` (champ calculé EE) | Local : lit `tolerance_min/max` depuis `quality.point`, compare à `value` |
| `quality.alert.create` | Identique | Identique (même modèle OCA) |
| SMS | Identique | Identique |

**Pseudo-code `_create_quality_check_oca` :**

```python
def _create_quality_check_oca(qcp_id, value, tag):
    uid, models = odoo_connect()

    check_id = models.execute_kw(ODOO_DB, uid, ODOO_KEY,
        "quality.check", "create",
        [{"point_id": qcp_id, "measure": value}])

    point = models.execute_kw(ODOO_DB, uid, ODOO_KEY,
        "quality.point", "read",
        [[qcp_id]], {"fields": ["tolerance_min", "tolerance_max"]})[0]

    result = "pass" if point["tolerance_min"] <= value <= point["tolerance_max"] else "fail"

    models.execute_kw(ODOO_DB, uid, ODOO_KEY,
        "quality.check", "write",
        [[check_id], {"quality_state": result}])

    if result == "fail":
        models.execute_kw(ODOO_DB, uid, ODOO_KEY,
            "quality.alert", "create",
            [{"name": f"[HACCP ALERTE] {tag} hors seuil: {value}"
                      f" (tol [{point['tolerance_min']}–{point['tolerance_max']}])"}])
        send_sms(tag, value, point["tolerance_min"], point["tolerance_max"])
        log.warning("ALERTE OCA — %s=%s → check #%s FAIL", tag, value, check_id)
    else:
        log.info("OK OCA — %s=%s → check #%s PASS", tag, value, check_id)

    return check_id, result
```

**vNode : zéro changement.** Le payload `{ qcp_id, value, tag, quality }` reste identique.

---

## Flux complet CE+OCA

```
vNode (RestApiClient)
  │  POST /quality-check { qcp_id, value, tag, quality }
  ▼
bridge.py  [ODOO_QUALITY_BACKEND=oca]
  ├─ quality < 64 → ignore
  ├─ quality.check.create()
  ├─ quality.point.read(tolerance_min, tolerance_max)
  ├─ calcul pass/fail local
  ├─ quality.check.write(quality_state)
  └─ si fail → quality.alert.create() + SMS
         │  XML-RPC
         ▼
  Odoo 19 CE (192.168.1.182:8019)
    quality_control_oca installé
    haccp_report installé (avec groupes HACCP propres)
    haccp_report_ce installé (override menus/security OCA)
         │
         ▼
  haccp_report.py — check_count / alert_count / rapport DDPP PDF
```

---

## Points de vérification à la disponibilité d'OCA 19.0

| Élément à vérifier | Valeur supposée (18.0) | Action si différente |
|---|---|---|
| Nom du module OCA | `quality_control_oca` | Adapter `__manifest__.py` de `haccp_report_ce` |
| Groupe user OCA | `quality_control_oca.group_quality_user` | Adapter CSV et menu_override.xml |
| Groupe manager OCA | `quality_control_oca.group_quality_manager` | Idem |
| Menu root OCA | `quality_control_oca.menu_quality_root` | Adapter menu_override.xml |
| Champ `quality.alert.name` | `name` (OCA) vs `title` (EE) | Adapter bridge.py et report_renderer.py |
| Champ `action_corrective` | Présent en OCA ? | Adapter report_template.xml si absent |

---

## Tests

Les tests unitaires existants (`test_haccp_report.py`, `test_haccp_calculs.py`,
`test_haccp_document.py`) tournent contre les modèles `quality.*` — compatibles EE et OCA. Aucun
test nouveau requis pour la logique métier.

Un test d'intégration manuel est suffisant pour valider le bridge en mode OCA :

```bash
ODOO_QUALITY_BACKEND=oca ODOO_URL=http://192.168.1.182:8019 \
  ODOO_DB=odoo19c_dev ODOO_KEY=xxx python3 bridge.py &
curl -s -X POST http://127.0.0.1:5001/quality-check \
  -H "Content-Type: application/json" \
  -d '{"qcp_id": 1, "value": 7.5, "tag": "Frigo_Test", "quality": 192}'
```

---

## Estimation d'effort

| Tâche | Effort |
|---|---|
| `haccp_groups.xml` + adapter `haccp_report` | 1h |
| Créer `haccp_report_ce` (4 fichiers) | 1h |
| Adapter `bridge.py` (mode OCA) | 1h |
| Vérification groupes OCA 19.0 + ajustements | À faire quand branche disponible |
| Test intégration CE | 0.5j |

**Total implémentation code :** ~3h. Validation OCA 19.0 : 0.5j en attente de la branche.
