# HACCP Dual-Compatible EE+CE/OCA — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre le module HACCP installable sur Odoo 19 CE (OCA quality_control_oca) sans toucher à la logique Python existante, en ajoutant un module compagnon léger et en adaptant bridge.py pour le mode OCA.

**Architecture:** On introduit des groupes HACCP propres dans `haccp_report` (supprime la dépendance aux groupes EE-only du module `quality`), puis on crée `haccp_report_ce` — un module squelette de 4 fichiers qui surcharge uniquement la sécurité et les menus avec les équivalents OCA. `bridge.py` reçoit un dispatcher `ee|oca` piloté par variable d'environnement.

**Tech Stack:** Odoo 19 CE/EE, Python 3, OCA quality_control_oca (18.0→19.0), XML-RPC, pytest (tests unitaires bridge)

---

## Carte des fichiers

| Action | Fichier | Responsabilité |
|---|---|---|
| Créer | `odoo-addons/haccp_report/security/haccp_groups.xml` | Groupes HACCP standalone (CE+EE) |
| Modifier | `odoo-addons/haccp_report/security/ir.model.access.csv` | Remplacer `quality.*` → `haccp_report.*` |
| Modifier | `odoo-addons/haccp_report/views/menu.xml` | Remplacer `quality.*` → `haccp_report.*` |
| Modifier | `odoo-addons/haccp_report/__manifest__.py` | Ajouter haccp_groups.xml, retirer note CE |
| Créer | `odoo-addons/haccp_report_ce/__init__.py` | Vide |
| Créer | `odoo-addons/haccp_report_ce/__manifest__.py` | Dépend haccp_report + quality_control_oca |
| Créer | `odoo-addons/haccp_report_ce/security/ir.model.access.csv` | Groupes OCA |
| Créer | `odoo-addons/haccp_report_ce/views/menu_override.xml` | Parent + groups OCA |
| Modifier | `infra/ops121s/odoo-bridge/bridge.py` | Dispatcher EE/OCA + _create_quality_check_oca |

---

## Task 1 — Groupes HACCP dans `haccp_report`

**Files:**
- Create: `odoo-addons/haccp_report/security/haccp_groups.xml`
- Modify: `odoo-addons/haccp_report/__manifest__.py`

- [ ] **Créer `haccp_groups.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data noupdate="1">
    <record id="group_haccp_user" model="res.groups">
      <field name="name">HACCP User</field>
    </record>
    <record id="group_haccp_manager" model="res.groups">
      <field name="name">HACCP Manager</field>
      <field name="implied_ids" eval="[(4, ref('haccp_report.group_haccp_user'))]"/>
    </record>
  </data>
</odoo>
```

- [ ] **Ajouter `haccp_groups.xml` dans `__manifest__.py` — avant `ir.model.access.csv`**

```python
'data': [
    'security/haccp_groups.xml',      # ← nouvelle ligne
    'security/ir.model.access.csv',
    'report/report_action.xml',
    'report/report_template.xml',
    'views/haccp_report_views.xml',
    'views/haccp_calculs_views.xml',
    'views/haccp_document_views.xml',
    'views/menu.xml',
    'views/quality_inherit.xml',
],
```

- [ ] **Retirer le commentaire CE-incompatible dans `__manifest__.py`**

Supprimer la ligne :
```python
# NOTE: requires Odoo Enterprise (quality_control module). Not compatible with Community Edition.
```

- [ ] **Commit**

```bash
git add odoo-addons/haccp_report/security/haccp_groups.xml \
        odoo-addons/haccp_report/__manifest__.py
git commit -m "feat(haccp): groupes HACCP standalone (CE+EE compatible)"
```

---

## Task 2 — Mettre à jour `ir.model.access.csv` dans `haccp_report`

**Files:**
- Modify: `odoo-addons/haccp_report/security/ir.model.access.csv`

- [ ] **Remplacer le contenu complet par la version avec groupes HACCP**

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_haccp_report_user,haccp.report user,model_haccp_report,haccp_report.group_haccp_user,1,1,1,0
access_haccp_report_manager,haccp.report manager,model_haccp_report,haccp_report.group_haccp_manager,1,1,1,1
access_haccp_dlc_user,haccp.dlc user,model_haccp_dlc,haccp_report.group_haccp_user,1,1,1,1
access_haccp_refroidissement_user,haccp.refroidissement user,model_haccp_refroidissement,haccp_report.group_haccp_user,1,1,1,1
access_haccp_dilution_user,haccp.dilution user,model_haccp_dilution,haccp_report.group_haccp_user,1,1,1,1
access_haccp_decongelation_user,haccp.decongelation user,model_haccp_decongelation,haccp_report.group_haccp_user,1,1,1,1
access_haccp_reassort_user,haccp.reassort user,model_haccp_reassort,haccp_report.group_haccp_user,1,1,1,1
access_haccp_document_user,haccp.document user,model_haccp_document,haccp_report.group_haccp_user,1,0,0,0
access_haccp_document_manager,haccp.document manager,model_haccp_document,haccp_report.group_haccp_manager,1,1,1,1
```

- [ ] **Commit**

```bash
git add odoo-addons/haccp_report/security/ir.model.access.csv
git commit -m "fix(haccp): remplacer groupes quality EE par groupes haccp_report"
```

---

## Task 3 — Mettre à jour `menu.xml` dans `haccp_report`

**Files:**
- Modify: `odoo-addons/haccp_report/views/menu.xml`

- [ ] **Remplacer toutes les occurrences de `quality.group_quality_user` par `haccp_report.group_haccp_user`**

5 occurrences dans le fichier. Le fichier final doit être :

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data>
    <menuitem
      id="menu_haccp_reports_root"
      name="Méthode HACCP"
      parent="quality_control.menu_quality_root"
      groups="haccp_report.group_haccp_user"
      sequence="25"/>

    <menuitem
      id="menu_haccp_report_ddpp"
      name="Rapports HACCP DDPP"
      parent="menu_haccp_reports_root"
      action="action_haccp_report"
      groups="haccp_report.group_haccp_user"
      sequence="10"/>

    <menuitem
      id="menu_haccp_calculs_root"
      name="Calculs et formules"
      parent="menu_haccp_reports_root"
      groups="haccp_report.group_haccp_user"
      sequence="20"/>

    <menuitem
      id="menu_haccp_dlc"
      name="DLC / DLUO"
      parent="menu_haccp_calculs_root"
      action="action_haccp_dlc"
      groups="haccp_report.group_haccp_user"
      sequence="10"/>

    <menuitem
      id="menu_haccp_refroidissement"
      name="Refroidissement"
      parent="menu_haccp_calculs_root"
      action="action_haccp_refroidissement"
      groups="haccp_report.group_haccp_user"
      sequence="20"/>

    <menuitem
      id="menu_haccp_reassort"
      name="Réassort"
      parent="menu_haccp_calculs_root"
      action="action_haccp_reassort"
      groups="haccp_report.group_haccp_user"
      sequence="50"/>

    <menuitem
      id="menu_haccp_decongelation"
      name="Décongélation"
      parent="menu_haccp_calculs_root"
      action="action_haccp_decongelation"
      groups="haccp_report.group_haccp_user"
      sequence="40"/>

    <menuitem
      id="menu_haccp_dilution"
      name="Dilution"
      parent="menu_haccp_calculs_root"
      action="action_haccp_dilution"
      groups="haccp_report.group_haccp_user"
      sequence="30"/>

    <menuitem
      id="menu_haccp_documents"
      name="Bibliothèque de documents"
      parent="menu_haccp_reports_root"
      action="action_haccp_document"
      groups="haccp_report.group_haccp_user"
      sequence="30"/>
  </data>
</odoo>
```

- [ ] **Commit**

```bash
git add odoo-addons/haccp_report/views/menu.xml
git commit -m "fix(haccp): menus — groupes quality EE → haccp_report"
```

---

## Task 4 — Vérifier que `haccp_report` s'installe toujours sur EE

**Files:** aucun (vérification uniquement)

- [ ] **Mettre à jour le module sur l'instance EE (port 8029)**

```bash
docker exec -it odoo19e bash -c \
  "odoo-bin -d odoo19e_dev -u haccp_report --stop-after-init 2>&1 | tail -20"
```

Résultat attendu : pas d'erreur `xmlrpclib.Fault` ni `KeyError` sur les groupes.

- [ ] **Lancer les tests existants sur EE**

```bash
docker exec -it odoo19e bash -c \
  "odoo-bin -d odoo19e_dev \
   --test-enable --stop-after-init \
   -i haccp_report 2>&1 | grep -E '(FAIL|ERROR|OK|Ran)'"
```

Résultat attendu : tous les tests passent (les tests utilisent `quality.check/point/alert` inchangés).

- [ ] **Si erreur — investiguer** : vérifier que `haccp_groups.xml` est chargé avant `ir.model.access.csv` dans le manifest (ordre critique).

---

## Task 5 — Créer le module `haccp_report_ce`

**Files:**
- Create: `odoo-addons/haccp_report_ce/__init__.py`
- Create: `odoo-addons/haccp_report_ce/__manifest__.py`
- Create: `odoo-addons/haccp_report_ce/security/ir.model.access.csv`
- Create: `odoo-addons/haccp_report_ce/views/menu_override.xml`

- [ ] **Créer la structure de répertoires**

```bash
mkdir -p odoo-addons/haccp_report_ce/security \
         odoo-addons/haccp_report_ce/views
touch odoo-addons/haccp_report_ce/__init__.py
```

- [ ] **Créer `__manifest__.py`**

```python
{
    'name': 'Rapport HACCP DDPP — Community Edition',
    'version': '19.0.1.0.0',
    'summary': 'Variante CE du module HACCP DDPP (OCA quality_control_oca)',
    'category': 'Quality',
    'author': 'AIFluence Digital',
    'depends': ['haccp_report', 'quality_control_oca', 'web', 'mail'],
    # NOTE: groupes OCA présumés depuis branche 18.0 — à vérifier sur 19.0
    'data': [
        'security/ir.model.access.csv',
        'views/menu_override.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
```

- [ ] **Créer `security/ir.model.access.csv`**

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_haccp_report_ce_user,haccp.report ce user,model_haccp_report,quality_control.group_quality_user,1,1,1,0
access_haccp_report_ce_manager,haccp.report ce manager,model_haccp_report,quality_control.group_quality_manager,1,1,1,1
access_haccp_dlc_ce_user,haccp.dlc ce user,model_haccp_dlc,quality_control.group_quality_user,1,1,1,1
access_haccp_refroidissement_ce_user,haccp.refroidissement ce user,model_haccp_refroidissement,quality_control.group_quality_user,1,1,1,1
access_haccp_dilution_ce_user,haccp.dilution ce user,model_haccp_dilution,quality_control.group_quality_user,1,1,1,1
access_haccp_decongelation_ce_user,haccp.decongelation ce user,model_haccp_decongelation,quality_control.group_quality_user,1,1,1,1
access_haccp_reassort_ce_user,haccp.reassort ce user,model_haccp_reassort,quality_control.group_quality_user,1,1,1,1
access_haccp_document_ce_user,haccp.document ce user,model_haccp_document,quality_control.group_quality_user,1,0,0,0
access_haccp_document_ce_manager,haccp.document ce manager,model_haccp_document,quality_control.group_quality_manager,1,1,1,1
```

> **Note :** `quality_control.group_quality_user` est le XML ID OCA présumé. Si l'installation
> échoue avec `External ID not found`, vérifier dans l'interface Odoo CE :
> Paramètres → Technique → Groupes → chercher "Quality".

- [ ] **Créer `views/menu_override.xml`**

Surcharge uniquement le menu racine `menu_haccp_reports_root` pour pointer vers le parent OCA.
Les sous-menus enfants héritent automatiquement du bon parent.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data>
    <menuitem
      id="haccp_report.menu_haccp_reports_root"
      parent="quality_control.menu_quality_root"
      groups="quality_control.group_quality_user"/>
  </data>
</odoo>
```

> **Note :** `quality_control.menu_quality_root` est l'XML ID du menu racine OCA. Même nom que
> le menu racine EE car OCA utilise le même nom de module `quality_control`. À vérifier sur 19.0.

- [ ] **Commit**

```bash
git add odoo-addons/haccp_report_ce/
git commit -m "feat(haccp-ce): module compagnon CE/OCA — zéro Python"
```

---

## Task 6 — Adapter `bridge.py` pour le mode OCA

**Files:**
- Modify: `infra/ops121s/odoo-bridge/bridge.py`

- [ ] **Ajouter la variable d'environnement et le dispatcher après la ligne `LISTEN_PORT`**

Après la ligne :
```python
LISTEN_PORT = int(os.environ.get("BRIDGE_PORT", "5001"))
```

Ajouter :
```python
QUALITY_BACKEND = os.environ.get("ODOO_QUALITY_BACKEND", "ee")  # ee | oca
```

- [ ] **Renommer `create_quality_check` en `_create_quality_check_ee`**

Changer la signature de la fonction existante :
```python
def _create_quality_check_ee(qcp_id: int, value: float, tag: str):
```

Le corps de la fonction reste **identique** — aucun changement interne.

- [ ] **Ajouter le dispatcher public et la fonction OCA après `_create_quality_check_ee`**

```python
def create_quality_check(qcp_id: int, value: float, tag: str):
    if QUALITY_BACKEND == "oca":
        return _create_quality_check_oca(qcp_id, value, tag)
    return _create_quality_check_ee(qcp_id, value, tag)


def _create_quality_check_oca(qcp_id: int, value: float, tag: str):
    uid, models = odoo_connect()

    check_id = models.execute_kw(
        ODOO_DB, uid, ODOO_KEY,
        "quality.check", "create",
        [{"point_id": qcp_id, "measure": value}],
    )

    point = models.execute_kw(
        ODOO_DB, uid, ODOO_KEY,
        "quality.point", "read",
        [[qcp_id]], {"fields": ["tolerance_min", "tolerance_max"]},
    )[0]
    tol_min = point["tolerance_min"]
    tol_max = point["tolerance_max"]

    result = "pass" if tol_min <= value <= tol_max else "fail"

    models.execute_kw(
        ODOO_DB, uid, ODOO_KEY,
        "quality.check", "write",
        [[check_id], {"quality_state": result}],
    )

    if result == "fail":
        models.execute_kw(
            ODOO_DB, uid, ODOO_KEY,
            "quality.alert", "create",
            [{"name": f"[HACCP ALERTE] {tag} hors seuil: {value}"
                      f" (tol [{tol_min}–{tol_max}])"}],
        )
        log.warning("ALERTE OCA — %s=%s hors seuil [%s–%s] → check #%s FAIL",
                    tag, value, tol_min, tol_max, check_id)
        send_sms(tag, value, tol_min, tol_max)
    else:
        log.info("OK OCA — %s=%s → check #%s PASS", tag, value, check_id)

    return check_id, result
```

- [ ] **Écrire le test unitaire pour `_create_quality_check_oca`**

Créer `infra/ops121s/odoo-bridge/test_bridge_oca.py` :

```python
"""Tests unitaires pour le mode OCA du bridge (sans instance Odoo réelle)."""
import sys
import types
import unittest
from unittest.mock import MagicMock, patch, call

# Stub minimal pour importer bridge sans dépendances réseau
import importlib, os
os.environ.setdefault("ODOO_KEY", "test")
os.environ["ODOO_QUALITY_BACKEND"] = "oca"

import bridge  # noqa: E402 — doit être importé après os.environ


class TestCreateQualityCheckOca(unittest.TestCase):

    def _make_models_mock(self, tol_min, tol_max):
        """Retourne un mock models XML-RPC avec les tolérances données."""
        m = MagicMock()
        # quality.check.create → check_id 42
        m.execute_kw.side_effect = self._side_effect_factory(tol_min, tol_max)
        return m

    @staticmethod
    def _side_effect_factory(tol_min, tol_max):
        call_count = [0]
        def side_effect(db, uid, key, model, method, args, kwargs=None):
            call_count[0] += 1
            if model == "quality.check" and method == "create":
                return 42
            if model == "quality.point" and method == "read":
                return [{"tolerance_min": tol_min, "tolerance_max": tol_max}]
            if model == "quality.check" and method == "write":
                return True
            if model == "quality.alert" and method == "create":
                return 99
            return None
        return side_effect

    def test_pass_result_when_value_within_tolerance(self):
        models_mock = self._make_models_mock(tol_min=-30.0, tol_max=4.0)
        with patch.object(bridge, "odoo_connect", return_value=(1, models_mock)), \
             patch.object(bridge, "send_sms") as sms_mock:
            check_id, result = bridge._create_quality_check_oca(1, 2.5, "Frigo")
        self.assertEqual(result, "pass")
        self.assertEqual(check_id, 42)
        sms_mock.assert_not_called()

    def test_fail_result_when_value_above_tolerance(self):
        models_mock = self._make_models_mock(tol_min=-30.0, tol_max=4.0)
        with patch.object(bridge, "odoo_connect", return_value=(1, models_mock)), \
             patch.object(bridge, "send_sms") as sms_mock:
            check_id, result = bridge._create_quality_check_oca(1, 7.0, "Frigo")
        self.assertEqual(result, "fail")
        sms_mock.assert_called_once_with("Frigo", 7.0, -30.0, 4.0)

    def test_fail_creates_quality_alert(self):
        models_mock = self._make_models_mock(tol_min=-30.0, tol_max=4.0)
        with patch.object(bridge, "odoo_connect", return_value=(1, models_mock)), \
             patch.object(bridge, "send_sms"):
            bridge._create_quality_check_oca(1, 7.0, "Frigo")
        alert_calls = [
            c for c in models_mock.execute_kw.call_args_list
            if c.args[3] == "quality.alert" and c.args[4] == "create"
        ]
        self.assertEqual(len(alert_calls), 1)

    def test_pass_does_not_create_quality_alert(self):
        models_mock = self._make_models_mock(tol_min=-30.0, tol_max=4.0)
        with patch.object(bridge, "odoo_connect", return_value=(1, models_mock)), \
             patch.object(bridge, "send_sms"):
            bridge._create_quality_check_oca(1, 2.5, "Frigo")
        alert_calls = [
            c for c in models_mock.execute_kw.call_args_list
            if c.args[3] == "quality.alert"
        ]
        self.assertEqual(len(alert_calls), 0)

    def test_dispatcher_routes_to_oca(self):
        """create_quality_check appelle _create_quality_check_oca quand QUALITY_BACKEND=oca."""
        with patch.object(bridge, "_create_quality_check_oca", return_value=(42, "pass")) as oca_mock, \
             patch.object(bridge, "_create_quality_check_ee") as ee_mock:
            bridge.create_quality_check(1, 2.5, "Frigo")
        oca_mock.assert_called_once_with(1, 2.5, "Frigo")
        ee_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Lancer les tests unitaires**

```bash
cd infra/ops121s/odoo-bridge
python -m pytest test_bridge_oca.py -v
```

Résultat attendu :
```
test_pass_result_when_value_within_tolerance PASSED
test_fail_result_when_value_above_tolerance PASSED
test_fail_creates_quality_alert PASSED
test_pass_does_not_create_quality_alert PASSED
test_dispatcher_routes_to_oca PASSED
5 passed in ...
```

- [ ] **Commit**

```bash
git add infra/ops121s/odoo-bridge/bridge.py \
        infra/ops121s/odoo-bridge/test_bridge_oca.py
git commit -m "feat(bridge): mode OCA avec dispatcher ODOO_QUALITY_BACKEND=ee|oca"
```

---

## Task 7 — Test d'intégration manuel (quand OCA 19.0 disponible)

**Files:** aucun — validation uniquement

- [ ] **Installer OCA quality_control_oca sur l'instance CE (port 8019)**

Depuis le dépôt OCA/quality-management, branche 19.0 :
```bash
# Copier les modules dans le addons path de l'instance CE
cp -r quality_control quality_control_oca /path/to/odoo19ce/addons/
docker restart odoo19c
```

- [ ] **Installer haccp_report puis haccp_report_ce**

Dans Odoo CE → Apps → chercher "haccp" → Installer `haccp_report` puis `haccp_report_ce`.

Si erreur `External ID not found` sur les groupes OCA :
1. Aller dans Paramètres → Technique → Groupes
2. Chercher "Quality" → noter les XML IDs réels
3. Mettre à jour `haccp_report_ce/security/ir.model.access.csv` et `views/menu_override.xml`
4. `docker exec odoo19c odoo-bin -d odoo19c_dev -u haccp_report_ce --stop-after-init`

- [ ] **Tester le bridge en mode OCA**

```bash
cd infra/ops121s/odoo-bridge
ODOO_QUALITY_BACKEND=oca \
ODOO_URL=http://192.168.1.182:8019 \
ODOO_DB=odoo19c_dev \
ODOO_KEY=<api_key> \
python bridge.py &

# Envoyer une mesure dans la limite → attendu: pass
curl -s -X POST http://127.0.0.1:5001/quality-check \
  -H "Content-Type: application/json" \
  -d '{"qcp_id": 1, "value": 2.5, "tag": "Frigo_Test", "quality": 192}' | python -m json.tool

# Envoyer une mesure hors limite → attendu: fail + quality.alert créé
curl -s -X POST http://127.0.0.1:5001/quality-check \
  -H "Content-Type: application/json" \
  -d '{"qcp_id": 1, "value": 9.0, "tag": "Frigo_Test", "quality": 192}' | python -m json.tool
```

Résultat attendu (pass) :
```json
{"status": "ok", "check_id": 1, "result": "pass"}
```

Résultat attendu (fail) :
```json
{"status": "ok", "check_id": 2, "result": "fail"}
```

Vérifier dans Odoo CE → Qualité → Contrôles que les deux enregistrements apparaissent.

- [ ] **Commit final si ajustements de noms OCA requis**

```bash
git add odoo-addons/haccp_report_ce/
git commit -m "fix(haccp-ce): ajuster XML IDs OCA 19.0 après vérification"
```
