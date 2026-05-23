# Méthode HACCP — Calculs, formules et bibliothèque de documents

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Étendre `haccp_report` avec un menu "Méthode HACCP" regroupant 5 calculateurs TransientModel et une bibliothèque de documents PDF synchronisée depuis aifluencedigital.com.

**Architecture:** 5 TransientModel (calculateurs éphémères, compute+depends, popup dialog) + 1 modèle permanent `haccp.document` (cache local des PDFs, sync via manifest JSON). Tout dans le module `haccp_report` existant.

**Tech Stack:** Odoo 19 Enterprise, Python 3, `requests` (sync HTTP), `hashlib` (comparaison MD5), `base64` (stockage attachment), `unittest.mock` (tests sync)

**Commandes de déploiement :**
- Tests : `./scripts/deploy-haccp-report.sh --test`
- Mise à jour : `./scripts/deploy-haccp-report.sh --update`

---

## Carte des fichiers

| Fichier | Action | Rôle |
|---|---|---|
| `models/__init__.py` | Modifier | Ajouter 6 imports |
| `models/haccp_dlc.py` | Créer | TransientModel DLC/DLUO |
| `models/haccp_refroidissement.py` | Créer | TransientModel refroidissement |
| `models/haccp_dilution.py` | Créer | TransientModel dilution |
| `models/haccp_decongelation.py` | Créer | TransientModel décongélation |
| `models/haccp_reassort.py` | Créer | TransientModel réassort |
| `models/haccp_document.py` | Créer | Modèle permanent + sync |
| `views/menu.xml` | Modifier | Renommage + nouveaux menus |
| `views/haccp_calculs_views.xml` | Créer | 5 forms + 5 actions |
| `views/haccp_document_views.xml` | Créer | List + kanban + server action |
| `security/ir.model.access.csv` | Modifier | Droits haccp.document |
| `__manifest__.py` | Modifier | Ajouter 2 fichiers vues |
| `tests/__init__.py` | Modifier | Ajouter 2 imports test |
| `tests/test_haccp_calculs.py` | Créer | Tests 5 calculateurs |
| `tests/test_haccp_document.py` | Créer | Tests modèle + sync |

---

## Task 0 : Infrastructure — renommage menu + manifest

**Files:**
- Modify: `odoo-addons/haccp_report/views/menu.xml`
- Modify: `odoo-addons/haccp_report/__manifest__.py`

- [ ] **Renommer le menu racine dans menu.xml**

Remplacer `name="Rapports HACCP"` par `name="Méthode HACCP"` :

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data>
    <menuitem
      id="menu_haccp_reports_root"
      name="Méthode HACCP"
      parent="quality_control.menu_quality_root"
      groups="quality.group_quality_user"
      sequence="25"/>

    <menuitem
      id="menu_haccp_report_ddpp"
      name="Rapports HACCP DDPP"
      parent="menu_haccp_reports_root"
      action="action_haccp_report"
      groups="quality.group_quality_user"
      sequence="10"/>
  </data>
</odoo>
```

- [ ] **Ajouter les 2 nouveaux fichiers vues dans `__manifest__.py`**

```python
'data': [
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

- [ ] **Créer `views/haccp_calculs_views.xml` vide (squelette)**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data>
    <!-- Calculateurs HACCP — views et actions -->
  </data>
</odoo>
```

- [ ] **Créer `views/haccp_document_views.xml` vide (squelette)**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data>
    <!-- Bibliothèque de documents HACCP -->
  </data>
</odoo>
```

- [ ] **Déployer et vérifier le renommage**

```bash
./scripts/deploy-haccp-report.sh --update
```

Aller dans Qualité → vérifier que le menu s'appelle bien "Méthode HACCP".

- [ ] **Commit**

```bash
git add odoo-addons/haccp_report/views/menu.xml \
        odoo-addons/haccp_report/views/haccp_calculs_views.xml \
        odoo-addons/haccp_report/views/haccp_document_views.xml \
        odoo-addons/haccp_report/__manifest__.py
git commit -m "feat(haccp): renommer menu Rapports HACCP → Méthode HACCP + squelettes vues"
```

---

## Task 1 : Calculateur DLC/DLUO

**Files:**
- Create: `odoo-addons/haccp_report/models/haccp_dlc.py`
- Create: `odoo-addons/haccp_report/tests/test_haccp_calculs.py`
- Modify: `odoo-addons/haccp_report/models/__init__.py`
- Modify: `odoo-addons/haccp_report/tests/__init__.py`
- Modify: `odoo-addons/haccp_report/views/haccp_calculs_views.xml`
- Modify: `odoo-addons/haccp_report/views/menu.xml`

- [ ] **Créer `tests/test_haccp_calculs.py` avec les tests DLC**

```python
from datetime import date, timedelta
from odoo.tests.common import TransactionCase


class TestHaccpDlc(TransactionCase):

    def _make_dlc(self, famille, condition, date_fab=None):
        return self.env['haccp.dlc'].create({
            'famille': famille,
            'condition': condition,
            'date_fabrication': date_fab or date.today(),
        })

    def test_duree_viande_crue_refrigere(self):
        rec = self._make_dlc('viande_crue', 'refrigere')
        self.assertEqual(rec.duree_jours, 3)

    def test_duree_poisson_congele(self):
        rec = self._make_dlc('poisson', 'congele')
        self.assertEqual(rec.duree_jours, 90)

    def test_duree_charcuterie_ambiant(self):
        rec = self._make_dlc('charcuterie', 'ambiant')
        self.assertEqual(rec.duree_jours, 30)

    def test_duree_ambiant_zero_viande(self):
        rec = self._make_dlc('viande_crue', 'ambiant')
        self.assertEqual(rec.duree_jours, 0)

    def test_date_limite_calculee(self):
        fab = date.today() - timedelta(days=1)
        rec = self._make_dlc('viande_crue', 'refrigere', fab)
        self.assertEqual(rec.date_limite, fab + timedelta(days=3))

    def test_statut_valide(self):
        fab = date.today()
        rec = self._make_dlc('charcuterie', 'refrigere', fab)
        self.assertEqual(rec.statut, '✓ Valide')

    def test_statut_expire(self):
        fab = date.today() - timedelta(days=10)
        rec = self._make_dlc('viande_crue', 'refrigere', fab)
        self.assertEqual(rec.statut, '✗ Expiré')

    def test_statut_expire_bientot(self):
        fab = date.today() - timedelta(days=2)
        rec = self._make_dlc('viande_crue', 'refrigere', fab)
        self.assertIn('⚠', rec.statut)

    def test_statut_non_applicable_ambiant(self):
        rec = self._make_dlc('viande_crue', 'ambiant')
        self.assertIn('⚠', rec.statut)
```

- [ ] **Mettre à jour `tests/__init__.py`**

```python
from . import test_haccp_report
from . import test_haccp_calculs
```

- [ ] **Lancer les tests pour vérifier l'échec**

```bash
./scripts/deploy-haccp-report.sh --test 2>&1 | grep -E 'ERROR|haccp.dlc|TestHaccpDlc'
```

Résultat attendu : erreur `AttributeError` ou `KeyError` sur `haccp.dlc` (modèle inexistant).

- [ ] **Créer `models/haccp_dlc.py`**

```python
from datetime import date as date_cls, timedelta
from odoo import models, fields, api

_DLC_TABLE = {
    ('viande_crue', 'refrigere'): 3,
    ('viande_crue', 'congele'): 90,
    ('viande_crue', 'ambiant'): 0,
    ('poisson', 'refrigere'): 2,
    ('poisson', 'congele'): 90,
    ('poisson', 'ambiant'): 0,
    ('charcuterie', 'refrigere'): 5,
    ('charcuterie', 'congele'): 90,
    ('charcuterie', 'ambiant'): 30,
    ('laitier', 'refrigere'): 7,
    ('laitier', 'congele'): 30,
    ('laitier', 'ambiant'): 0,
    ('plat_cuisine', 'refrigere'): 3,
    ('plat_cuisine', 'congele'): 90,
    ('plat_cuisine', 'ambiant'): 0,
    ('legumes', 'refrigere'): 5,
    ('legumes', 'congele'): 180,
    ('legumes', 'ambiant'): 7,
    ('autre', 'refrigere'): 3,
    ('autre', 'congele'): 90,
    ('autre', 'ambiant'): 7,
}


class HaccpDlc(models.TransientModel):
    _name = 'haccp.dlc'
    _description = 'Calculateur DLC / DLUO'

    famille = fields.Selection([
        ('viande_crue', 'Viande crue'),
        ('poisson', 'Poisson'),
        ('charcuterie', 'Charcuterie'),
        ('laitier', 'Produit laitier'),
        ('plat_cuisine', 'Plat cuisiné'),
        ('legumes', 'Légumes'),
        ('autre', 'Autre'),
    ], string='Famille', required=True)

    condition = fields.Selection([
        ('refrigere', 'Réfrigéré (+4°C)'),
        ('congele', 'Congelé (-18°C)'),
        ('ambiant', 'Ambiant'),
    ], string='Condition de conservation', required=True)

    date_fabrication = fields.Date(
        string='Date de fabrication / ouverture', required=True,
        default=fields.Date.today,
    )

    duree_jours = fields.Integer(string='Durée (jours)', compute='_compute_dlc')
    date_limite = fields.Date(string='Date limite', compute='_compute_dlc')
    statut = fields.Char(string='Statut', compute='_compute_dlc')

    @api.depends('famille', 'condition', 'date_fabrication')
    def _compute_dlc(self):
        today = date_cls.today()
        for rec in self:
            duree = _DLC_TABLE.get((rec.famille, rec.condition), 0)
            rec.duree_jours = duree
            if not rec.date_fabrication or not rec.famille or not rec.condition:
                rec.date_limite = False
                rec.statut = ''
                continue
            if duree == 0:
                rec.date_limite = False
                rec.statut = '⚠ Conservation non recommandée à cette température'
                continue
            limite = rec.date_fabrication + timedelta(days=duree)
            rec.date_limite = limite
            jours = (limite - today).days
            if jours < 0:
                rec.statut = '✗ Expiré'
            elif jours <= 2:
                rec.statut = f'⚠ Expire bientôt (≤2j) — {jours}j restant(s)'
            else:
                rec.statut = f'✓ Valide — {jours} jours restants'
```

- [ ] **Mettre à jour `models/__init__.py`**

```python
from . import haccp_report
from . import report_renderer
from . import haccp_dlc
```

- [ ] **Lancer les tests**

```bash
./scripts/deploy-haccp-report.sh --test 2>&1 | grep -E 'OK|FAIL|ERROR|TestHaccpDlc'
```

Résultat attendu : tous les tests `TestHaccpDlc` passent.

- [ ] **Ajouter la vue form et l'action dans `haccp_calculs_views.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data>

    <!-- ===== DLC / DLUO ===== -->
    <record id="view_haccp_dlc_form" model="ir.ui.view">
      <field name="name">haccp.dlc.form</field>
      <field name="model">haccp.dlc</field>
      <field name="arch" type="xml">
        <form string="Calculateur DLC / DLUO">
          <group string="Paramètres">
            <field name="famille"/>
            <field name="condition"/>
            <field name="date_fabrication"/>
          </group>
          <group string="Résultat">
            <field name="duree_jours" readonly="1"/>
            <field name="date_limite" readonly="1"/>
            <field name="statut" readonly="1"/>
          </group>
          <footer>
            <button string="Fermer" class="btn-secondary" special="cancel"/>
          </footer>
        </form>
      </field>
    </record>

    <record id="action_haccp_dlc" model="ir.actions.act_window">
      <field name="name">DLC / DLUO</field>
      <field name="res_model">haccp.dlc</field>
      <field name="view_mode">form</field>
      <field name="target">new</field>
    </record>

  </data>
</odoo>
```

- [ ] **Ajouter les menus dans `menu.xml`**

Ajouter après le menu `menu_haccp_report_ddpp` existant :

```xml
    <!-- Groupe Calculs et formules -->
    <menuitem
      id="menu_haccp_calculs_root"
      name="Calculs et formules"
      parent="menu_haccp_reports_root"
      groups="quality.group_quality_user"
      sequence="20"/>

    <menuitem
      id="menu_haccp_dlc"
      name="DLC / DLUO"
      parent="menu_haccp_calculs_root"
      action="action_haccp_dlc"
      groups="quality.group_quality_user"
      sequence="10"/>
```

- [ ] **Déployer et tester manuellement dans Odoo**

```bash
./scripts/deploy-haccp-report.sh --update
```

Vérifier : Qualité → Méthode HACCP → Calculs et formules → DLC / DLUO → popup s'ouvre, résultats calculés en temps réel.

- [ ] **Commit**

```bash
git add odoo-addons/haccp_report/models/haccp_dlc.py \
        odoo-addons/haccp_report/models/__init__.py \
        odoo-addons/haccp_report/tests/test_haccp_calculs.py \
        odoo-addons/haccp_report/tests/__init__.py \
        odoo-addons/haccp_report/views/haccp_calculs_views.xml \
        odoo-addons/haccp_report/views/menu.xml
git commit -m "feat(haccp): calculateur DLC/DLUO"
```

---

## Task 2 : Calculateur Refroidissement rapide

**Files:**
- Create: `odoo-addons/haccp_report/models/haccp_refroidissement.py`
- Modify: `odoo-addons/haccp_report/models/__init__.py`
- Modify: `odoo-addons/haccp_report/tests/test_haccp_calculs.py`
- Modify: `odoo-addons/haccp_report/views/haccp_calculs_views.xml`
- Modify: `odoo-addons/haccp_report/views/menu.xml`

- [ ] **Ajouter les tests refroidissement dans `test_haccp_calculs.py`**

Ajouter la classe suivante à la fin du fichier :

```python
from datetime import datetime


class TestHaccpRefroidissement(TransactionCase):

    def _make_ref(self, delta_minutes=0):
        debut = fields.Datetime.now() - timedelta(minutes=delta_minutes)
        return self.env['haccp.refroidissement'].create({'heure_debut': debut})

    def test_heure_limite_plus_2h(self):
        from odoo import fields as ofields
        debut = ofields.Datetime.now()
        rec = self.env['haccp.refroidissement'].create({'heure_debut': debut})
        diff = rec.heure_limite - debut
        self.assertAlmostEqual(diff.total_seconds(), 7200, delta=5)

    def test_heure_mi_parcours_plus_1h(self):
        from odoo import fields as ofields
        debut = ofields.Datetime.now()
        rec = self.env['haccp.refroidissement'].create({'heure_debut': debut})
        diff = rec.heure_mi_parcours - debut
        self.assertAlmostEqual(diff.total_seconds(), 3600, delta=5)

    def test_statut_en_cours(self):
        rec = self._make_ref(delta_minutes=30)
        self.assertEqual(rec.statut, '⏳ EN COURS')

    def test_statut_depasse(self):
        rec = self._make_ref(delta_minutes=130)
        self.assertEqual(rec.statut, '✗ FENÊTRE DÉPASSÉE')
```

- [ ] **Créer `models/haccp_refroidissement.py`**

```python
from datetime import timedelta
from odoo import models, fields, api


class HaccpRefroidissement(models.TransientModel):
    _name = 'haccp.refroidissement'
    _description = 'Minuteur de refroidissement HACCP'

    heure_debut = fields.Datetime(
        string='Heure de début du refroidissement',
        required=True,
        default=fields.Datetime.now,
    )
    heure_limite = fields.Datetime(
        string='Heure limite (+2h max)',
        compute='_compute_refroidissement',
    )
    heure_mi_parcours = fields.Datetime(
        string='Mi-parcours (+1h, objectif ≤21°C)',
        compute='_compute_refroidissement',
    )
    statut = fields.Char(string='Statut', compute='_compute_refroidissement')

    @api.depends('heure_debut')
    def _compute_refroidissement(self):
        for rec in self:
            if not rec.heure_debut:
                rec.heure_limite = False
                rec.heure_mi_parcours = False
                rec.statut = ''
                continue
            rec.heure_limite = rec.heure_debut + timedelta(hours=2)
            rec.heure_mi_parcours = rec.heure_debut + timedelta(hours=1)
            now = fields.Datetime.now()
            rec.statut = '⏳ EN COURS' if now < rec.heure_limite else '✗ FENÊTRE DÉPASSÉE'
```

- [ ] **Mettre à jour `models/__init__.py`**

```python
from . import haccp_report
from . import report_renderer
from . import haccp_dlc
from . import haccp_refroidissement
```

- [ ] **Lancer les tests**

```bash
./scripts/deploy-haccp-report.sh --test 2>&1 | grep -E 'OK|FAIL|ERROR|TestHaccpRefroid'
```

Résultat attendu : tous les tests `TestHaccpRefroidissement` passent.

- [ ] **Ajouter la vue et l'action dans `haccp_calculs_views.xml`**

Ajouter après le bloc DLC :

```xml
    <!-- ===== Refroidissement rapide ===== -->
    <record id="view_haccp_refroidissement_form" model="ir.ui.view">
      <field name="name">haccp.refroidissement.form</field>
      <field name="model">haccp.refroidissement</field>
      <field name="arch" type="xml">
        <form string="Minuteur de refroidissement HACCP">
          <group string="Paramètres">
            <field name="heure_debut"/>
          </group>
          <group string="Résultat (règle : +63°C → +10°C en &lt; 2h)">
            <field name="heure_mi_parcours" readonly="1"/>
            <field name="heure_limite" readonly="1"/>
            <field name="statut" readonly="1"/>
          </group>
          <footer>
            <button string="Fermer" class="btn-secondary" special="cancel"/>
          </footer>
        </form>
      </field>
    </record>

    <record id="action_haccp_refroidissement" model="ir.actions.act_window">
      <field name="name">Refroidissement</field>
      <field name="res_model">haccp.refroidissement</field>
      <field name="view_mode">form</field>
      <field name="target">new</field>
    </record>
```

- [ ] **Ajouter le menu dans `menu.xml`**

```xml
    <menuitem
      id="menu_haccp_refroidissement"
      name="Refroidissement"
      parent="menu_haccp_calculs_root"
      action="action_haccp_refroidissement"
      groups="quality.group_quality_user"
      sequence="20"/>
```

- [ ] **Déployer et vérifier**

```bash
./scripts/deploy-haccp-report.sh --update
```

- [ ] **Commit**

```bash
git add odoo-addons/haccp_report/models/haccp_refroidissement.py \
        odoo-addons/haccp_report/models/__init__.py \
        odoo-addons/haccp_report/tests/test_haccp_calculs.py \
        odoo-addons/haccp_report/views/haccp_calculs_views.xml \
        odoo-addons/haccp_report/views/menu.xml
git commit -m "feat(haccp): calculateur refroidissement rapide"
```

---

## Task 3 : Calculateur Dilution

**Files:**
- Create: `odoo-addons/haccp_report/models/haccp_dilution.py`
- Modify: `odoo-addons/haccp_report/models/__init__.py`
- Modify: `odoo-addons/haccp_report/tests/test_haccp_calculs.py`
- Modify: `odoo-addons/haccp_report/views/haccp_calculs_views.xml`
- Modify: `odoo-addons/haccp_report/views/menu.xml`

- [ ] **Ajouter les tests dilution dans `test_haccp_calculs.py`**

```python
class TestHaccpDilution(TransactionCase):

    def _make_dil(self, volume, ratio, ratio_custom=0):
        return self.env['haccp.dilution'].create({
            'volume_total': volume,
            'ratio': ratio,
            'ratio_custom': ratio_custom,
        })

    def test_ratio_1_10_produit(self):
        rec = self._make_dil(1.0, '10')
        # 1L / (10+1) * 1000 = 90.909... ml
        self.assertAlmostEqual(rec.volume_produit_ml, 1000 / 11, places=1)

    def test_ratio_1_10_eau(self):
        rec = self._make_dil(1.0, '10')
        self.assertAlmostEqual(rec.volume_eau_l, 1.0 - (1 / 11), places=3)

    def test_ratio_1_100(self):
        rec = self._make_dil(2.0, '100')
        self.assertAlmostEqual(rec.volume_produit_ml, 2000 / 101, places=1)

    def test_ratio_custom(self):
        rec = self._make_dil(1.0, 'custom', ratio_custom=30)
        self.assertAlmostEqual(rec.volume_produit_ml, 1000 / 31, places=1)

    def test_volume_zero_retourne_zero(self):
        rec = self._make_dil(0.0, '10')
        self.assertEqual(rec.volume_produit_ml, 0.0)
        self.assertEqual(rec.volume_eau_l, 0.0)

    def test_ratio_custom_zero_retourne_zero(self):
        rec = self._make_dil(1.0, 'custom', ratio_custom=0)
        self.assertEqual(rec.volume_produit_ml, 0.0)
```

- [ ] **Créer `models/haccp_dilution.py`**

```python
from odoo import models, fields, api

_RATIO_VALUES = {'10': 10, '20': 20, '50': 50, '100': 100}


class HaccpDilution(models.TransientModel):
    _name = 'haccp.dilution'
    _description = 'Convertisseur de dilution produit nettoyant'

    volume_total = fields.Float(
        string='Volume total souhaité (litres)',
        required=True,
        digits=(10, 3),
    )
    ratio = fields.Selection([
        ('10', '1:10'),
        ('20', '1:20'),
        ('50', '1:50'),
        ('100', '1:100'),
        ('custom', 'Personnalisé'),
    ], string='Ratio de dilution', required=True, default='10')

    ratio_custom = fields.Integer(string='Ratio personnalisé (1:N)')

    volume_produit_ml = fields.Float(
        string='Volume produit pur (ml)',
        compute='_compute_dilution',
        digits=(10, 1),
    )
    volume_eau_l = fields.Float(
        string='Volume eau (litres)',
        compute='_compute_dilution',
        digits=(10, 3),
    )

    @api.depends('volume_total', 'ratio', 'ratio_custom')
    def _compute_dilution(self):
        for rec in self:
            ratio_n = rec.ratio_custom if rec.ratio == 'custom' else _RATIO_VALUES.get(rec.ratio, 0)
            if rec.volume_total > 0 and ratio_n > 0:
                vol_produit_l = rec.volume_total / (ratio_n + 1)
                rec.volume_produit_ml = vol_produit_l * 1000
                rec.volume_eau_l = rec.volume_total - vol_produit_l
            else:
                rec.volume_produit_ml = 0.0
                rec.volume_eau_l = 0.0
```

- [ ] **Mettre à jour `models/__init__.py`**

```python
from . import haccp_report
from . import report_renderer
from . import haccp_dlc
from . import haccp_refroidissement
from . import haccp_dilution
```

- [ ] **Lancer les tests**

```bash
./scripts/deploy-haccp-report.sh --test 2>&1 | grep -E 'OK|FAIL|ERROR|TestHaccpDilution'
```

Résultat attendu : tous les tests `TestHaccpDilution` passent.

- [ ] **Ajouter la vue et l'action dans `haccp_calculs_views.xml`**

```xml
    <!-- ===== Dilution produit nettoyant ===== -->
    <record id="view_haccp_dilution_form" model="ir.ui.view">
      <field name="name">haccp.dilution.form</field>
      <field name="model">haccp.dilution</field>
      <field name="arch" type="xml">
        <form string="Convertisseur de dilution">
          <group string="Paramètres">
            <field name="volume_total"/>
            <field name="ratio"/>
            <field name="ratio_custom" invisible="ratio != 'custom'"/>
          </group>
          <group string="Résultat">
            <field name="volume_produit_ml" readonly="1"/>
            <field name="volume_eau_l" readonly="1"/>
          </group>
          <footer>
            <button string="Fermer" class="btn-secondary" special="cancel"/>
          </footer>
        </form>
      </field>
    </record>

    <record id="action_haccp_dilution" model="ir.actions.act_window">
      <field name="name">Dilution</field>
      <field name="res_model">haccp.dilution</field>
      <field name="view_mode">form</field>
      <field name="target">new</field>
    </record>
```

- [ ] **Ajouter le menu dans `menu.xml`**

```xml
    <menuitem
      id="menu_haccp_dilution"
      name="Dilution"
      parent="menu_haccp_calculs_root"
      action="action_haccp_dilution"
      groups="quality.group_quality_user"
      sequence="30"/>
```

- [ ] **Déployer et vérifier**

```bash
./scripts/deploy-haccp-report.sh --update
```

- [ ] **Commit**

```bash
git add odoo-addons/haccp_report/models/haccp_dilution.py \
        odoo-addons/haccp_report/models/__init__.py \
        odoo-addons/haccp_report/tests/test_haccp_calculs.py \
        odoo-addons/haccp_report/views/haccp_calculs_views.xml \
        odoo-addons/haccp_report/views/menu.xml
git commit -m "feat(haccp): calculateur dilution produit nettoyant"
```

---

## Task 4 : Calculateur Décongélation

**Files:**
- Create: `odoo-addons/haccp_report/models/haccp_decongelation.py`
- Modify: `odoo-addons/haccp_report/models/__init__.py`
- Modify: `odoo-addons/haccp_report/tests/test_haccp_calculs.py`
- Modify: `odoo-addons/haccp_report/views/haccp_calculs_views.xml`
- Modify: `odoo-addons/haccp_report/views/menu.xml`

- [ ] **Ajouter les tests décongélation dans `test_haccp_calculs.py`**

```python
class TestHaccpDecongelation(TransactionCase):

    def _make_dec(self, famille, poids, debut=None):
        from odoo import fields as ofields
        return self.env['haccp.decongelation'].create({
            'famille': famille,
            'poids_kg': poids,
            'debut_decongelation': debut or ofields.Datetime.now(),
        })

    def test_duree_viande_entiere_2kg(self):
        rec = self._make_dec('viande_entiere', 2.0)
        self.assertAlmostEqual(rec.duree_heures, 48.0, places=1)

    def test_duree_poisson_1kg(self):
        rec = self._make_dec('poisson', 1.0)
        self.assertAlmostEqual(rec.duree_heures, 12.0, places=1)

    def test_duree_minimum_2h(self):
        rec = self._make_dec('viande_hachee', 0.1)
        self.assertEqual(rec.duree_heures, 2.0)

    def test_fin_decongelation_calculee(self):
        from odoo import fields as ofields
        debut = ofields.Datetime.now()
        rec = self.env['haccp.decongelation'].create({
            'famille': 'volaille',
            'poids_kg': 1.0,
            'debut_decongelation': debut,
        })
        diff = rec.fin_decongelation - debut
        self.assertAlmostEqual(diff.total_seconds(), 20 * 3600, delta=60)

    def test_dlc_secondaire_j_plus_1(self):
        from odoo import fields as ofields
        debut = ofields.Datetime.now()
        rec = self.env['haccp.decongelation'].create({
            'famille': 'poisson',
            'poids_kg': 1.0,
            'debut_decongelation': debut,
        })
        expected = (debut + timedelta(hours=12)).date() + timedelta(days=1)
        self.assertEqual(rec.dlc_secondaire, expected)
```

- [ ] **Créer `models/haccp_decongelation.py`**

```python
from datetime import timedelta
from odoo import models, fields, api

_HEURES_PAR_KG = {
    'viande_entiere': 24,
    'volaille': 20,
    'poisson': 12,
    'viande_hachee': 8,
}
_DUREE_MIN = 2.0


class HaccpDecongelation(models.TransientModel):
    _name = 'haccp.decongelation'
    _description = 'Calculateur de décongélation'

    famille = fields.Selection([
        ('viande_entiere', 'Viande entière'),
        ('volaille', 'Volaille'),
        ('poisson', 'Poisson'),
        ('viande_hachee', 'Viande hachée'),
    ], string="Type d'aliment", required=True)

    poids_kg = fields.Float(string='Poids (kg)', required=True, digits=(10, 3))

    debut_decongelation = fields.Datetime(
        string='Début de décongélation',
        required=True,
        default=fields.Datetime.now,
    )

    duree_heures = fields.Float(
        string='Durée estimée (heures)',
        compute='_compute_decongelation',
        digits=(10, 1),
    )
    fin_decongelation = fields.Datetime(
        string='Fin de décongélation estimée',
        compute='_compute_decongelation',
    )
    dlc_secondaire = fields.Date(
        string='DLC secondaire (après décongélation)',
        compute='_compute_decongelation',
    )

    @api.depends('famille', 'poids_kg', 'debut_decongelation')
    def _compute_decongelation(self):
        for rec in self:
            if not rec.famille or not rec.poids_kg or not rec.debut_decongelation:
                rec.duree_heures = 0.0
                rec.fin_decongelation = False
                rec.dlc_secondaire = False
                continue
            h_par_kg = _HEURES_PAR_KG.get(rec.famille, 24)
            duree = max(rec.poids_kg * h_par_kg, _DUREE_MIN)
            rec.duree_heures = duree
            fin = rec.debut_decongelation + timedelta(hours=duree)
            rec.fin_decongelation = fin
            rec.dlc_secondaire = fin.date() + timedelta(days=1)
```

- [ ] **Mettre à jour `models/__init__.py`**

```python
from . import haccp_report
from . import report_renderer
from . import haccp_dlc
from . import haccp_refroidissement
from . import haccp_dilution
from . import haccp_decongelation
```

- [ ] **Lancer les tests**

```bash
./scripts/deploy-haccp-report.sh --test 2>&1 | grep -E 'OK|FAIL|ERROR|TestHaccpDecong'
```

Résultat attendu : tous les tests `TestHaccpDecongelation` passent.

- [ ] **Ajouter la vue et l'action dans `haccp_calculs_views.xml`**

```xml
    <!-- ===== Décongélation ===== -->
    <record id="view_haccp_decongelation_form" model="ir.ui.view">
      <field name="name">haccp.decongelation.form</field>
      <field name="model">haccp.decongelation</field>
      <field name="arch" type="xml">
        <form string="Calculateur de décongélation">
          <group string="Paramètres">
            <field name="famille"/>
            <field name="poids_kg"/>
            <field name="debut_decongelation"/>
          </group>
          <group string="Résultat (décongélation au réfrigérateur +4°C)">
            <field name="duree_heures" readonly="1"/>
            <field name="fin_decongelation" readonly="1"/>
            <field name="dlc_secondaire" readonly="1"/>
          </group>
          <footer>
            <button string="Fermer" class="btn-secondary" special="cancel"/>
          </footer>
        </form>
      </field>
    </record>

    <record id="action_haccp_decongelation" model="ir.actions.act_window">
      <field name="name">Décongélation</field>
      <field name="res_model">haccp.decongelation</field>
      <field name="view_mode">form</field>
      <field name="target">new</field>
    </record>
```

- [ ] **Ajouter le menu dans `menu.xml`**

```xml
    <menuitem
      id="menu_haccp_decongelation"
      name="Décongélation"
      parent="menu_haccp_calculs_root"
      action="action_haccp_decongelation"
      groups="quality.group_quality_user"
      sequence="40"/>
```

- [ ] **Déployer et vérifier**

```bash
./scripts/deploy-haccp-report.sh --update
```

- [ ] **Commit**

```bash
git add odoo-addons/haccp_report/models/haccp_decongelation.py \
        odoo-addons/haccp_report/models/__init__.py \
        odoo-addons/haccp_report/tests/test_haccp_calculs.py \
        odoo-addons/haccp_report/views/haccp_calculs_views.xml \
        odoo-addons/haccp_report/views/menu.xml
git commit -m "feat(haccp): calculateur décongélation"
```

---

## Task 5 : Calculateur Réassort

**Files:**
- Create: `odoo-addons/haccp_report/models/haccp_reassort.py`
- Modify: `odoo-addons/haccp_report/models/__init__.py`
- Modify: `odoo-addons/haccp_report/tests/test_haccp_calculs.py`
- Modify: `odoo-addons/haccp_report/views/haccp_calculs_views.xml`
- Modify: `odoo-addons/haccp_report/views/menu.xml`

- [ ] **Ajouter les tests réassort dans `test_haccp_calculs.py`**

```python
class TestHaccpReassort(TransactionCase):

    def _make_reas(self, stock, conso, delai, securite=0.0):
        return self.env['haccp.reassort'].create({
            'stock_actuel': stock,
            'conso_journaliere': conso,
            'delai_livraison': delai,
            'stock_securite': securite,
        })

    def test_point_commande(self):
        rec = self._make_reas(100, 10, 3, 5)
        # 10 * 3 + 5 = 35
        self.assertAlmostEqual(rec.point_commande, 35.0, places=2)

    def test_jours_restants(self):
        rec = self._make_reas(100, 10, 3, 5)
        # (100 - 35) / 10 = 6.5
        self.assertAlmostEqual(rec.jours_restants, 6.5, places=2)

    def test_statut_ok(self):
        rec = self._make_reas(100, 10, 3, 5)
        self.assertEqual(rec.statut, '✓ OK')

    def test_statut_commander(self):
        rec = self._make_reas(30, 10, 3, 5)
        # point_commande = 35 > stock = 30 → commander
        self.assertEqual(rec.statut, '✗ COMMANDER MAINTENANT')

    def test_statut_exactement_au_point(self):
        rec = self._make_reas(35, 10, 3, 5)
        self.assertEqual(rec.statut, '✗ COMMANDER MAINTENANT')

    def test_conso_zero_jours_restants_zero(self):
        rec = self._make_reas(100, 0, 3, 5)
        self.assertEqual(rec.jours_restants, 0.0)
```

- [ ] **Créer `models/haccp_reassort.py`**

```python
from odoo import models, fields, api


class HaccpReassort(models.TransientModel):
    _name = 'haccp.reassort'
    _description = 'Calculateur de point de réassort'

    stock_actuel = fields.Float(string='Stock actuel (unités)', required=True, digits=(10, 2))
    conso_journaliere = fields.Float(
        string='Consommation journalière (unités/jour)',
        required=True,
        digits=(10, 2),
    )
    delai_livraison = fields.Integer(string='Délai de livraison (jours)', required=True)
    stock_securite = fields.Float(string='Stock de sécurité (unités)', digits=(10, 2))

    point_commande = fields.Float(
        string='Point de commande',
        compute='_compute_reassort',
        digits=(10, 2),
    )
    jours_restants = fields.Float(
        string='Jours avant point de commande',
        compute='_compute_reassort',
        digits=(10, 1),
    )
    statut = fields.Char(string='Statut', compute='_compute_reassort')

    @api.depends('stock_actuel', 'conso_journaliere', 'delai_livraison', 'stock_securite')
    def _compute_reassort(self):
        for rec in self:
            pc = rec.conso_journaliere * rec.delai_livraison + rec.stock_securite
            rec.point_commande = pc
            rec.jours_restants = (
                (rec.stock_actuel - pc) / rec.conso_journaliere
                if rec.conso_journaliere > 0 else 0.0
            )
            rec.statut = '✗ COMMANDER MAINTENANT' if rec.stock_actuel <= pc else '✓ OK'
```

- [ ] **Mettre à jour `models/__init__.py`**

```python
from . import haccp_report
from . import report_renderer
from . import haccp_dlc
from . import haccp_refroidissement
from . import haccp_dilution
from . import haccp_decongelation
from . import haccp_reassort
```

- [ ] **Lancer les tests**

```bash
./scripts/deploy-haccp-report.sh --test 2>&1 | grep -E 'OK|FAIL|ERROR|TestHaccpReassort'
```

Résultat attendu : tous les tests `TestHaccpReassort` passent.

- [ ] **Ajouter la vue et l'action dans `haccp_calculs_views.xml`**

```xml
    <!-- ===== Réassort ===== -->
    <record id="view_haccp_reassort_form" model="ir.ui.view">
      <field name="name">haccp.reassort.form</field>
      <field name="model">haccp.reassort</field>
      <field name="arch" type="xml">
        <form string="Calculateur de point de réassort">
          <group string="Paramètres">
            <field name="stock_actuel"/>
            <field name="conso_journaliere"/>
            <field name="delai_livraison"/>
            <field name="stock_securite"/>
          </group>
          <group string="Résultat">
            <field name="point_commande" readonly="1"/>
            <field name="jours_restants" readonly="1"/>
            <field name="statut" readonly="1"/>
          </group>
          <footer>
            <button string="Fermer" class="btn-secondary" special="cancel"/>
          </footer>
        </form>
      </field>
    </record>

    <record id="action_haccp_reassort" model="ir.actions.act_window">
      <field name="name">Réassort</field>
      <field name="res_model">haccp.reassort</field>
      <field name="view_mode">form</field>
      <field name="target">new</field>
    </record>
```

- [ ] **Ajouter le menu dans `menu.xml`**

```xml
    <menuitem
      id="menu_haccp_reassort"
      name="Réassort"
      parent="menu_haccp_calculs_root"
      action="action_haccp_reassort"
      groups="quality.group_quality_user"
      sequence="50"/>
```

- [ ] **Déployer et vérifier tous les calculateurs**

```bash
./scripts/deploy-haccp-report.sh --update
```

Vérifier chaque calculateur manuellement dans Odoo.

- [ ] **Commit**

```bash
git add odoo-addons/haccp_report/models/haccp_reassort.py \
        odoo-addons/haccp_report/models/__init__.py \
        odoo-addons/haccp_report/tests/test_haccp_calculs.py \
        odoo-addons/haccp_report/views/haccp_calculs_views.xml \
        odoo-addons/haccp_report/views/menu.xml
git commit -m "feat(haccp): calculateur réassort — complète la suite Calculs et formules"
```

---

## Task 6 : Modèle haccp.document + sécurité

**Files:**
- Create: `odoo-addons/haccp_report/models/haccp_document.py`
- Create: `odoo-addons/haccp_report/tests/test_haccp_document.py`
- Modify: `odoo-addons/haccp_report/models/__init__.py`
- Modify: `odoo-addons/haccp_report/tests/__init__.py`
- Modify: `odoo-addons/haccp_report/security/ir.model.access.csv`

- [ ] **Créer `tests/test_haccp_document.py`**

```python
import base64
import json
from unittest.mock import MagicMock, patch
from odoo.tests.common import TransactionCase


class TestHaccpDocumentModel(TransactionCase):

    def test_create_document(self):
        doc = self.env['haccp.document'].create({
            'name': 'Fiche test',
            'category': 'releves',
            'source_url': 'https://example.com/test.pdf',
        })
        self.assertEqual(doc.name, 'Fiche test')
        self.assertEqual(doc.category, 'releves')

    def test_statut_non_telecharge(self):
        doc = self.env['haccp.document'].create({
            'name': 'Fiche test',
            'category': 'releves',
        })
        self.assertEqual(doc.statut, '⬇ Non téléchargé')

    def test_statut_telecharge(self):
        attachment = self.env['ir.attachment'].create({
            'name': 'test.pdf',
            'datas': base64.b64encode(b'%PDF-1.4').decode(),
            'mimetype': 'application/pdf',
        })
        doc = self.env['haccp.document'].create({
            'name': 'Fiche test',
            'category': 'releves',
            'attachment_id': attachment.id,
        })
        self.assertEqual(doc.statut, '✓ Téléchargé')


class TestHaccpDocumentSync(TransactionCase):

    def _make_mock_responses(self, manifest, pdf_content=b'%PDF-1.4 test'):
        mock_manifest = MagicMock()
        mock_manifest.json.return_value = manifest
        mock_manifest.raise_for_status.return_value = None

        mock_pdf = MagicMock()
        mock_pdf.content = pdf_content
        mock_pdf.raise_for_status.return_value = None

        return [mock_manifest, mock_pdf]

    def test_sync_creates_new_document(self):
        manifest = {'documents': [{
            'name': 'Fiche températures',
            'category': 'releves',
            'description': 'Test',
            'url': 'https://example.com/fiche-temp.pdf',
            'hash': 'abc123',
        }]}
        with patch('odoo.addons.haccp_report.models.haccp_document.requests.get') as mock_get:
            mock_get.side_effect = self._make_mock_responses(manifest)
            self.env['haccp.document'].action_sync_documents()

        doc = self.env['haccp.document'].search([
            ('source_url', '=', 'https://example.com/fiche-temp.pdf')
        ])
        self.assertEqual(len(doc), 1)
        self.assertEqual(doc.name, 'Fiche températures')
        self.assertTrue(doc.attachment_id)
        self.assertEqual(doc.statut, '✓ Téléchargé')

    def test_sync_unchanged_skips_download(self):
        import hashlib
        pdf_content = b'%PDF-1.4 test'
        file_hash = hashlib.md5(pdf_content).hexdigest()
        attachment = self.env['ir.attachment'].create({
            'name': 'existing.pdf',
            'datas': base64.b64encode(pdf_content).decode(),
            'mimetype': 'application/pdf',
        })
        doc = self.env['haccp.document'].create({
            'name': 'Doc existant',
            'category': 'releves',
            'source_url': 'https://example.com/existing.pdf',
            'file_hash': file_hash,
            'attachment_id': attachment.id,
        })
        manifest = {'documents': [{
            'name': 'Doc existant',
            'category': 'releves',
            'description': '',
            'url': 'https://example.com/existing.pdf',
            'hash': file_hash,
        }]}
        with patch('odoo.addons.haccp_report.models.haccp_document.requests.get') as mock_get:
            mock_manifest = MagicMock()
            mock_manifest.json.return_value = manifest
            mock_manifest.raise_for_status.return_value = None
            mock_get.return_value = mock_manifest
            self.env['haccp.document'].action_sync_documents()

        # get appelé une seule fois (manifest seulement, pas de PDF)
        self.assertEqual(mock_get.call_count, 1)

    def test_sync_updates_changed_document(self):
        import hashlib
        old_pdf = b'%PDF-1.4 old'
        new_pdf = b'%PDF-1.4 new'
        new_hash = hashlib.md5(new_pdf).hexdigest()
        attachment = self.env['ir.attachment'].create({
            'name': 'doc.pdf',
            'datas': base64.b64encode(old_pdf).decode(),
            'mimetype': 'application/pdf',
        })
        doc = self.env['haccp.document'].create({
            'name': 'Doc',
            'category': 'releves',
            'source_url': 'https://example.com/doc.pdf',
            'file_hash': hashlib.md5(old_pdf).hexdigest(),
            'attachment_id': attachment.id,
        })
        manifest = {'documents': [{
            'name': 'Doc',
            'category': 'releves',
            'description': '',
            'url': 'https://example.com/doc.pdf',
            'hash': new_hash,
        }]}
        with patch('odoo.addons.haccp_report.models.haccp_document.requests.get') as mock_get:
            mock_get.side_effect = self._make_mock_responses(manifest, new_pdf)
            self.env['haccp.document'].action_sync_documents()

        doc.invalidate_recordset()
        self.assertEqual(doc.file_hash, new_hash)
```

- [ ] **Mettre à jour `tests/__init__.py`**

```python
from . import test_haccp_report
from . import test_haccp_calculs
from . import test_haccp_document
```

- [ ] **Créer `models/haccp_document.py`**

```python
import base64
import hashlib
import logging

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

MANIFEST_URL = 'https://aifluencedigital.com/haccp/manifest.json'


class HaccpDocument(models.Model):
    _name = 'haccp.document'
    _description = 'Document HACCP'
    _order = 'category, name'

    name = fields.Char(string='Nom', required=True)
    category = fields.Selection([
        ('releves', 'Relevés & traçabilité'),
        ('affiches', 'Affiches de sensibilisation'),
        ('reglementation', 'Réglementation'),
        ('fiches_pratiques', 'Fiches pratiques'),
    ], string='Catégorie', required=True)
    description = fields.Text(string='Description')
    source_url = fields.Char(string='URL source')
    attachment_id = fields.Many2one(
        'ir.attachment', string='Fichier PDF', ondelete='set null',
    )
    date_sync = fields.Datetime(string='Dernière synchronisation')
    file_hash = fields.Char(string='Hash MD5')

    statut = fields.Char(string='Statut', compute='_compute_statut')

    @api.depends('attachment_id')
    def _compute_statut(self):
        for rec in self:
            rec.statut = '✓ Téléchargé' if rec.attachment_id else '⬇ Non téléchargé'

    @api.model
    def action_sync_documents(self):
        try:
            resp = requests.get(MANIFEST_URL, timeout=10)
            resp.raise_for_status()
            manifest = resp.json()
        except Exception as exc:
            raise UserError(_('Impossible de récupérer le manifest : %s') % str(exc))

        added = updated = unchanged = 0
        for entry in manifest.get('documents', []):
            doc = self.search([('source_url', '=', entry['url'])], limit=1)
            remote_hash = entry.get('hash', '')

            if not doc:
                doc = self.create({
                    'name': entry['name'],
                    'category': entry['category'],
                    'description': entry.get('description', ''),
                    'source_url': entry['url'],
                })

            if doc.file_hash == remote_hash and doc.attachment_id:
                unchanged += 1
                continue

            try:
                pdf_resp = requests.get(entry['url'], timeout=30)
                pdf_resp.raise_for_status()
                pdf_data = pdf_resp.content
            except Exception as exc:
                _logger.warning('Échec téléchargement %s : %s', entry['url'], exc)
                continue

            local_hash = hashlib.md5(pdf_data).hexdigest()
            filename = entry['url'].rstrip('/').split('/')[-1]
            encoded = base64.b64encode(pdf_data).decode()

            if doc.attachment_id:
                doc.attachment_id.write({'datas': encoded, 'name': filename})
                updated += 1
            else:
                attachment = self.env['ir.attachment'].create({
                    'name': filename,
                    'datas': encoded,
                    'res_model': 'haccp.document',
                    'res_id': doc.id,
                    'mimetype': 'application/pdf',
                })
                doc.attachment_id = attachment
                added += 1

            doc.write({
                'file_hash': local_hash,
                'date_sync': fields.Datetime.now(),
                'name': entry['name'],
                'category': entry['category'],
                'description': entry.get('description', ''),
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Synchronisation terminée'),
                'message': _(
                    '%d ajouté(s), %d mis à jour, %d inchangé(s)'
                ) % (added, updated, unchanged),
                'type': 'success',
                'sticky': False,
            },
        }
```

- [ ] **Mettre à jour `models/__init__.py`**

```python
from . import haccp_report
from . import report_renderer
from . import haccp_dlc
from . import haccp_refroidissement
from . import haccp_dilution
from . import haccp_decongelation
from . import haccp_reassort
from . import haccp_document
```

- [ ] **Mettre à jour `security/ir.model.access.csv`**

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_haccp_report_user,haccp.report user,model_haccp_report,quality.group_quality_user,1,1,1,0
access_haccp_report_manager,haccp.report manager,model_haccp_report,quality.group_quality_manager,1,1,1,1
access_haccp_document_user,haccp.document user,model_haccp_document,quality.group_quality_user,1,0,0,0
access_haccp_document_manager,haccp.document manager,model_haccp_document,quality.group_quality_manager,1,1,1,1
```

- [ ] **Lancer les tests**

```bash
./scripts/deploy-haccp-report.sh --test 2>&1 | grep -E 'OK|FAIL|ERROR|TestHaccpDocument'
```

Résultat attendu : tous les tests `TestHaccpDocumentModel` et `TestHaccpDocumentSync` passent.

- [ ] **Commit**

```bash
git add odoo-addons/haccp_report/models/haccp_document.py \
        odoo-addons/haccp_report/models/__init__.py \
        odoo-addons/haccp_report/tests/test_haccp_document.py \
        odoo-addons/haccp_report/tests/__init__.py \
        odoo-addons/haccp_report/security/ir.model.access.csv
git commit -m "feat(haccp): modèle haccp.document + sync manifest JSON"
```

---

## Task 7 : Vue bibliothèque de documents + menu

**Files:**
- Modify: `odoo-addons/haccp_report/views/haccp_document_views.xml`
- Modify: `odoo-addons/haccp_report/views/menu.xml`

- [ ] **Remplir `views/haccp_document_views.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data>

    <!-- Vue liste -->
    <record id="view_haccp_document_list" model="ir.ui.view">
      <field name="name">haccp.document.list</field>
      <field name="model">haccp.document</field>
      <field name="arch" type="xml">
        <list string="Bibliothèque de documents HACCP">
          <field name="name"/>
          <field name="category"/>
          <field name="description"/>
          <field name="date_sync"/>
          <field name="statut"/>
          <field name="attachment_id" widget="many2one" string="Fichier"/>
        </list>
      </field>
    </record>

    <!-- Vue kanban -->
    <record id="view_haccp_document_kanban" model="ir.ui.view">
      <field name="name">haccp.document.kanban</field>
      <field name="model">haccp.document</field>
      <field name="arch" type="xml">
        <kanban default_group_by="category">
          <field name="name"/>
          <field name="category"/>
          <field name="description"/>
          <field name="statut"/>
          <field name="attachment_id"/>
          <templates>
            <t t-name="card">
              <div class="oe_kanban_global_click">
                <strong><field name="name"/></strong>
                <div class="text-muted small"><field name="description"/></div>
                <div class="mt-2">
                  <span class="badge rounded-pill bg-info"><field name="statut"/></span>
                </div>
                <div t-if="record.attachment_id.raw_value" class="mt-2">
                  <a t-attf-href="/web/content/#{record.attachment_id.raw_value}?download=true"
                     class="btn btn-sm btn-primary" target="_blank">
                    Télécharger
                  </a>
                </div>
              </div>
            </t>
          </templates>
        </kanban>
      </field>
    </record>

    <!-- Vue form (lecture seule) -->
    <record id="view_haccp_document_form" model="ir.ui.view">
      <field name="name">haccp.document.form</field>
      <field name="model">haccp.document</field>
      <field name="arch" type="xml">
        <form string="Document HACCP">
          <group>
            <field name="name"/>
            <field name="category"/>
            <field name="description"/>
            <field name="source_url"/>
            <field name="attachment_id"/>
            <field name="date_sync" readonly="1"/>
            <field name="statut" readonly="1"/>
          </group>
        </form>
      </field>
    </record>

    <!-- Action serveur : Mettre à jour les documents (managers uniquement) -->
    <record id="action_haccp_document_sync_server" model="ir.actions.server">
      <field name="name">Mettre à jour les documents</field>
      <field name="model_id" ref="model_haccp_document"/>
      <field name="binding_model_id" ref="model_haccp_document"/>
      <field name="binding_view_types">list</field>
      <field name="state">code</field>
      <field name="code">action = env['haccp.document'].action_sync_documents()</field>
      <field name="groups_id" eval="[(4, ref('quality.group_quality_manager'))]"/>
    </record>

    <!-- Action principale (list + kanban) -->
    <record id="action_haccp_document" model="ir.actions.act_window">
      <field name="name">Bibliothèque de documents</field>
      <field name="res_model">haccp.document</field>
      <field name="view_mode">list,kanban,form</field>
    </record>

  </data>
</odoo>
```

- [ ] **Ajouter le menu Bibliothèque dans `menu.xml`**

```xml
    <!-- Bibliothèque de documents -->
    <menuitem
      id="menu_haccp_documents"
      name="Bibliothèque de documents"
      parent="menu_haccp_reports_root"
      action="action_haccp_document"
      groups="quality.group_quality_user"
      sequence="30"/>
```

- [ ] **Déployer et vérifier**

```bash
./scripts/deploy-haccp-report.sh --update
```

Vérifier :
- Qualité → Méthode HACCP → Bibliothèque de documents → liste vide s'affiche
- Vue kanban accessible
- Le menu Action (⚙️) dans la liste montre "Mettre à jour les documents" pour un manager

- [ ] **Commit**

```bash
git add odoo-addons/haccp_report/views/haccp_document_views.xml \
        odoo-addons/haccp_report/views/menu.xml
git commit -m "feat(haccp): vue bibliothèque de documents + action sync manager"
```

---

## Vérification finale

- [ ] **Lancer la suite de tests complète**

```bash
./scripts/deploy-haccp-report.sh --test 2>&1 | tail -30
```

Résultat attendu : 0 erreur, 0 échec sur `TestHaccpDlc`, `TestHaccpRefroidissement`, `TestHaccpDilution`, `TestHaccpDecongelation`, `TestHaccpReassort`, `TestHaccpDocumentModel`, `TestHaccpDocumentSync`.

- [ ] **Parcours complet dans Odoo**

Vérifier manuellement :
1. Qualité → Méthode HACCP → menu renommé ✓
2. Rapports HACCP DDPP → inchangé ✓
3. Calculs et formules → 5 sous-menus, chaque popup s'ouvre et calcule ✓
4. Bibliothèque de documents → liste/kanban vide ✓
5. Action "Mettre à jour les documents" visible pour manager ✓ (invisible pour user simple ✓)
