# Étiquettes DLC secondaire — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre à un cuisinier connecté au portail Odoo (sans licence utilisateur interne) d'imprimer une étiquette DLC secondaire sur l'imprimante réseau OXHOO TLP200, avec traçabilité persistante et QR de clôture.

**Architecture:** Module `haccp_report` étendu : un nouveau modèle persistant `haccp.dlc.ouverture` (portal.mixin + mail.thread) stocke chaque ouverture ; un contrôleur HTTP dédié gère deux pages portail (création + consultation/clôture) en s'appuyant sur `sudo()` après vérification manuelle d'un groupe `group_haccp_kitchen` (aucun droit ACL direct pour le portail) ; un module utilitaire construit le ZPL et l'envoie en direct sur le port 9100 de l'imprimante.

**Tech Stack:** Odoo 19 EE (module Python/XML), `portal.mixin`, `http.Controller` Odoo, QWeb, socket TCP brut (ZPL), tests `odoo.tests.common.TransactionCase` / `HttpCase`.

**Référence :** spec validée dans `docs/superpowers/specs/2026-07-19-etiquettes-dlc-design.md`.

---

## Task 1: Extraire la table de durées DLC dans un module partagé

Refactor pur — aucun changement de comportement. Le wizard `haccp.dlc` et le nouveau modèle `haccp.dlc.ouverture` doivent partager la même table de durées et les mêmes listes de sélection, sans duplication.

**Files:**
- Create: `odoo-addons/haccp_report/models/haccp_dlc_table.py`
- Modify: `odoo-addons/haccp_report/models/haccp_dlc.py`
- Modify: `odoo-addons/haccp_report/models/__init__.py`

- [ ] **Step 1: Lancer les tests existants comme filet de sécurité (baseline)**

Run: `./scripts/deploy-haccp-report.sh --test`
Expected: tous les tests passent (aucune régression avant de commencer).

- [ ] **Step 2: Créer le module partagé**

```python
# odoo-addons/haccp_report/models/haccp_dlc_table.py

DLC_TABLE = {
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

DLC_FAMILLE_SELECTION = [
    ('viande_crue', 'Viande crue'),
    ('poisson', 'Poisson'),
    ('charcuterie', 'Charcuterie'),
    ('laitier', 'Produit laitier'),
    ('plat_cuisine', 'Plat cuisiné'),
    ('legumes', 'Légumes'),
    ('autre', 'Autre'),
]

DLC_CONDITION_SELECTION = [
    ('refrigere', 'Réfrigéré (+4°C)'),
    ('congele', 'Congelé (-18°C)'),
    ('ambiant', 'Ambiant'),
]
```

- [ ] **Step 3: Faire pointer `haccp_dlc.py` vers le module partagé**

Remplacer tout le contenu de `odoo-addons/haccp_report/models/haccp_dlc.py` par :

```python
from datetime import date as date_cls, timedelta
from odoo import models, fields, api
from .haccp_dlc_table import DLC_TABLE, DLC_FAMILLE_SELECTION, DLC_CONDITION_SELECTION


class HaccpDlc(models.TransientModel):
    _name = 'haccp.dlc'
    _description = 'Calculateur DLC / DLUO'

    famille = fields.Selection(DLC_FAMILLE_SELECTION, string='Famille', required=True)
    condition = fields.Selection(DLC_CONDITION_SELECTION, string='Condition de conservation', required=True)

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
            if not rec.date_fabrication or not rec.famille or not rec.condition:
                rec.duree_jours = 0
                rec.date_limite = False
                rec.statut = ''
                continue
            duree = DLC_TABLE.get((rec.famille, rec.condition), 0)
            rec.duree_jours = duree
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

- [ ] **Step 4: Enregistrer le nouveau module dans `__init__.py`**

Modifier `odoo-addons/haccp_report/models/__init__.py` :

```python
from . import haccp_report
from . import report_renderer
from . import haccp_dlc_table
from . import haccp_dlc
from . import haccp_refroidissement
from . import haccp_dilution
from . import haccp_decongelation
from . import haccp_reassort
from . import haccp_document
```

- [ ] **Step 5: Relancer les tests — aucune régression**

Run: `./scripts/deploy-haccp-report.sh --test`
Expected: mêmes résultats qu'à l'étape 1 (tous les tests `test_haccp_calculs.py` passent toujours, en particulier `TestHaccpDlc`).

- [ ] **Step 6: Commit**

```bash
git add odoo-addons/haccp_report/models/haccp_dlc_table.py odoo-addons/haccp_report/models/haccp_dlc.py odoo-addons/haccp_report/models/__init__.py
git commit -m "refactor(haccp): extraire la table DLC dans un module partagé"
```

---

## Task 2: Modèle `haccp.dlc.ouverture`

**Files:**
- Create: `odoo-addons/haccp_report/models/haccp_dlc_ouverture.py`
- Create: `odoo-addons/haccp_report/data/haccp_dlc_ouverture_sequence.xml`
- Modify: `odoo-addons/haccp_report/models/__init__.py`
- Modify: `odoo-addons/haccp_report/__manifest__.py`
- Test: `odoo-addons/haccp_report/tests/test_haccp_dlc_ouverture.py`

- [ ] **Step 1: Écrire les tests (RED)**

```python
# odoo-addons/haccp_report/tests/test_haccp_dlc_ouverture.py
from datetime import timedelta
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestHaccpDlcOuverture(TransactionCase):

    def _make(self, **overrides):
        vals = {
            'product_name': 'Sauce tomate maison',
            'famille': 'plat_cuisine',
            'condition': 'refrigere',
            'date_ouverture': fields.Datetime.now(),
            'operateur_id': self.env.user.id,
        }
        vals.update(overrides)
        return self.env['haccp.dlc.ouverture'].create(vals)

    def test_reference_auto_generee(self):
        rec = self._make()
        self.assertNotEqual(rec.reference, 'Nouveau')
        self.assertTrue(rec.reference)

    def test_duree_calculee_depuis_table_partagee(self):
        rec = self._make(famille='plat_cuisine', condition='refrigere')
        self.assertEqual(rec.duree_jours, 3)

    def test_date_limite_calculee(self):
        ouverture = fields.Datetime.now()
        rec = self._make(famille='laitier', condition='refrigere', date_ouverture=ouverture)
        self.assertEqual(rec.date_limite, ouverture.date() + timedelta(days=7))

    def test_statut_par_defaut_ouvert(self):
        rec = self._make()
        self.assertEqual(rec.statut, 'ouvert')

    def test_action_cloturer_termine(self):
        rec = self._make()
        rec.action_cloturer('termine')
        self.assertEqual(rec.statut, 'termine')
        self.assertTrue(rec.date_cloture)

    def test_action_cloturer_deja_cloture_leve_erreur(self):
        rec = self._make()
        rec.action_cloturer('jete')
        with self.assertRaises(UserError):
            rec.action_cloturer('termine')

    def test_est_expire_quand_date_limite_passee_et_ouvert(self):
        ouverture = fields.Datetime.now() - timedelta(days=30)
        rec = self._make(famille='laitier', condition='refrigere', date_ouverture=ouverture)
        self.assertTrue(rec.est_expire)

    def test_est_expire_faux_si_cloture(self):
        ouverture = fields.Datetime.now() - timedelta(days=30)
        rec = self._make(famille='laitier', condition='refrigere', date_ouverture=ouverture)
        rec.action_cloturer('jete')
        self.assertFalse(rec.est_expire)

    def test_access_token_genere_a_la_creation(self):
        rec = self._make()
        self.assertTrue(rec.access_token)
```

Ajouter l'import dans `odoo-addons/haccp_report/tests/__init__.py` :

```python
from . import test_haccp_report
from . import test_haccp_calculs
from . import test_haccp_document
from . import test_haccp_dlc_ouverture
```

- [ ] **Step 2: Vérifier que les tests échouent**

Run: `./scripts/deploy-haccp-report.sh --test`
Expected: échec — `haccp.dlc.ouverture` n'existe pas encore (le module ne s'installera même pas tant que le modèle n'est pas défini si des tests y font référence ; c'est attendu à ce stade).

- [ ] **Step 3: Créer la séquence pour la référence**

```xml
<!-- odoo-addons/haccp_report/data/haccp_dlc_ouverture_sequence.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data noupdate="1">
    <record id="seq_haccp_dlc_ouverture" model="ir.sequence">
      <field name="name">Référence ouverture DLC</field>
      <field name="code">haccp.dlc.ouverture</field>
      <field name="prefix">%(year)s-%(doy)s-</field>
      <field name="padding">3</field>
      <field name="company_id" eval="False"/>
    </record>
  </data>
</odoo>
```

- [ ] **Step 4: Implémenter le modèle**

```python
# odoo-addons/haccp_report/models/haccp_dlc_ouverture.py
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .haccp_dlc_table import DLC_TABLE, DLC_FAMILLE_SELECTION, DLC_CONDITION_SELECTION


class HaccpDlcOuverture(models.Model):
    _name = 'haccp.dlc.ouverture'
    _description = 'Ouverture DLC secondaire (étiquette cuisine)'
    _inherit = ['portal.mixin', 'mail.thread']
    _order = 'date_ouverture desc'

    reference = fields.Char(
        string='Référence', required=True, copy=False, readonly=True, default='Nouveau'
    )
    product_id = fields.Many2one('product.template', string='Produit (catalogue)')
    product_name = fields.Char(string='Nom du produit', required=True)
    famille = fields.Selection(DLC_FAMILLE_SELECTION, string='Famille', required=True)
    condition = fields.Selection(
        DLC_CONDITION_SELECTION, string='Condition de conservation', required=True
    )
    date_ouverture = fields.Datetime(
        string="Date d'ouverture", required=True, default=fields.Datetime.now
    )
    operateur_id = fields.Many2one(
        'res.users', string='Opérateur', required=True, readonly=True
    )
    duree_jours = fields.Integer(string='Durée (jours)', compute='_compute_dlc', store=True)
    date_limite = fields.Date(string='Date limite', compute='_compute_dlc', store=True)
    statut = fields.Selection([
        ('ouvert', 'Ouvert'),
        ('termine', 'Terminé'),
        ('jete', 'Jeté'),
    ], string='Statut', default='ouvert', required=True, readonly=True)
    date_cloture = fields.Datetime(string='Date de clôture', readonly=True)
    est_expire = fields.Boolean(string='Expiré', compute='_compute_est_expire')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'Nouveau') == 'Nouveau':
                vals['reference'] = (
                    self.env['ir.sequence'].next_by_code('haccp.dlc.ouverture') or 'Nouveau'
                )
        records = super().create(vals_list)
        for record in records:
            record._portal_ensure_token()
        return records

    @api.depends('famille', 'condition', 'date_ouverture')
    def _compute_dlc(self):
        for rec in self:
            duree = DLC_TABLE.get((rec.famille, rec.condition), 0)
            rec.duree_jours = duree
            if rec.date_ouverture and duree:
                rec.date_limite = rec.date_ouverture.date() + timedelta(days=duree)
            else:
                rec.date_limite = False

    @api.depends('statut', 'date_limite')
    def _compute_est_expire(self):
        today = fields.Date.today()
        for rec in self:
            rec.est_expire = bool(
                rec.statut == 'ouvert' and rec.date_limite and rec.date_limite < today
            )

    def action_cloturer(self, statut):
        self.ensure_one()
        if statut not in ('termine', 'jete'):
            raise ValueError('statut de clôture invalide : %s' % statut)
        if self.statut != 'ouvert':
            raise UserError(_('Cette étiquette est déjà clôturée.'))
        self.write({'statut': statut, 'date_cloture': fields.Datetime.now()})

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = '/haccp/etiquette/%s/%s' % (rec.id, rec.access_token or '')
```

- [ ] **Step 5: Enregistrer le modèle et la dépendance `portal`**

Modifier `odoo-addons/haccp_report/models/__init__.py` (ajouter après `haccp_dlc_table`) :

```python
from . import haccp_report
from . import report_renderer
from . import haccp_dlc_table
from . import haccp_dlc
from . import haccp_dlc_ouverture
from . import haccp_refroidissement
from . import haccp_dilution
from . import haccp_decongelation
from . import haccp_reassort
from . import haccp_document
```

Modifier `odoo-addons/haccp_report/__manifest__.py` — `depends` et `data` :

```python
    'depends': ['quality_control', 'web', 'mail', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'data/haccp_dlc_ouverture_sequence.xml',
        'report/report_action.xml',
        'report/report_template.xml',
        'views/haccp_report_views.xml',
        'views/haccp_calculs_views.xml',
        'views/haccp_document_views.xml',
        'views/menu.xml',
        'views/quality_inherit.xml',
    ],
```

(Le fichier `security/ir.model.access.csv` recevra la ligne pour ce nouveau modèle à la Task 3 — il est déjà dans `data` donc rien d'autre à ajouter ici.)

- [ ] **Step 6: Installer le module et lancer les tests**

Run: `./scripts/deploy-haccp-report.sh --update` puis `./scripts/deploy-haccp-report.sh --test`
Expected: le module s'installe (accès pas encore configuré pour `haccp.dlc.ouverture`, mais le modèle admin/superuser a tous les droits donc les tests `TransactionCase` — qui tournent par défaut en tant qu'admin — doivent maintenant passer). Tous les tests de `test_haccp_dlc_ouverture.py` passent.

- [ ] **Step 7: Redémarrer le conteneur si nécessaire**

Si des erreurs de type "module Python non rechargé" apparaissent : `ssh christian@192.168.1.182 "docker restart odoo19e_app"` puis relancer `--test`.

- [ ] **Step 8: Commit**

```bash
git add odoo-addons/haccp_report/models/haccp_dlc_ouverture.py odoo-addons/haccp_report/data/haccp_dlc_ouverture_sequence.xml odoo-addons/haccp_report/models/__init__.py odoo-addons/haccp_report/__manifest__.py odoo-addons/haccp_report/tests/test_haccp_dlc_ouverture.py odoo-addons/haccp_report/tests/__init__.py
git commit -m "feat(haccp): modèle haccp.dlc.ouverture (DLC secondaire persistante)"
```

---

## Task 3: Sécurité — groupe cuisine et ACL restrictive

Aucun droit direct sur `haccp.dlc.ouverture` pour le groupe portail cuisine : tout passe par le contrôleur en `sudo()`. Ce comportement doit être vérifié par un test qui prouve qu'un utilisateur portail ne peut PAS écrire directement sur le modèle.

**Files:**
- Create: `odoo-addons/haccp_report/security/haccp_kitchen_security.xml`
- Modify: `odoo-addons/haccp_report/security/ir.model.access.csv`
- Modify: `odoo-addons/haccp_report/__manifest__.py`
- Test: `odoo-addons/haccp_report/tests/test_haccp_dlc_ouverture_security.py`

- [ ] **Step 1: Écrire le test de sécurité (RED)**

```python
# odoo-addons/haccp_report/tests/test_haccp_dlc_ouverture_security.py
from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestHaccpDlcOuvertureSecurity(TransactionCase):

    def setUp(self):
        super().setUp()
        self.portal_user = self.env['res.users'].create({
            'name': 'Cuisinier Test',
            'login': 'cuisinier.test@example.com',
            'groups_id': [(6, 0, [
                self.env.ref('base.group_portal').id,
                self.env.ref('haccp_report.group_haccp_kitchen').id,
            ])],
        })

    def test_utilisateur_portail_cuisine_ne_peut_pas_creer_directement(self):
        with self.assertRaises(AccessError):
            self.env['haccp.dlc.ouverture'].with_user(self.portal_user).create({
                'product_name': 'Test',
                'famille': 'autre',
                'condition': 'refrigere',
                'date_ouverture': fields.Datetime.now(),
                'operateur_id': self.portal_user.id,
            })

    def test_utilisateur_portail_cuisine_ne_peut_pas_lire_directement(self):
        rec = self.env['haccp.dlc.ouverture'].create({
            'product_name': 'Test',
            'famille': 'autre',
            'condition': 'refrigere',
            'date_ouverture': fields.Datetime.now(),
            'operateur_id': self.env.user.id,
        })
        with self.assertRaises(AccessError):
            rec.with_user(self.portal_user).read(['product_name'])
```

Ajouter l'import dans `odoo-addons/haccp_report/tests/__init__.py` :

```python
from . import test_haccp_report
from . import test_haccp_calculs
from . import test_haccp_document
from . import test_haccp_dlc_ouverture
from . import test_haccp_dlc_ouverture_security
```

- [ ] **Step 2: Vérifier que les tests échouent**

Run: `./scripts/deploy-haccp-report.sh --test`
Expected: échec — `haccp_report.group_haccp_kitchen` n'existe pas encore (`ValueError` sur `self.env.ref(...)`).

- [ ] **Step 3: Créer le groupe cuisine**

```xml
<!-- odoo-addons/haccp_report/security/haccp_kitchen_security.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data>
    <record id="group_haccp_kitchen" model="res.groups">
      <field name="name">HACCP — Cuisine (portail)</field>
      <field name="category_id" ref="base.module_category_hidden"/>
      <field name="implied_ids" eval="[(4, ref('base.group_portal'))]"/>
      <field name="comment">Utilisateurs portail autorisés à imprimer des étiquettes DLC depuis la cuisine. Aucun droit ACL direct : tout passe par le contrôleur haccp_portal.py en sudo().</field>
    </record>
  </data>
</odoo>
```

- [ ] **Step 4: Ajouter la ligne ACL (aucun accès portail — seuls les groupes internes existants gardent leur accès habituel)**

Ajouter à la fin de `odoo-addons/haccp_report/security/ir.model.access.csv` :

```
access_haccp_dlc_ouverture_user,haccp.dlc.ouverture user,model_haccp_dlc_ouverture,quality.group_quality_user,1,1,1,0
access_haccp_dlc_ouverture_manager,haccp.dlc.ouverture manager,model_haccp_dlc_ouverture,quality.group_quality_manager,1,1,1,1
```

(Volontairement, aucune ligne pour `haccp_report.group_haccp_kitchen` : c'est ce qui garantit qu'un utilisateur portail ne peut rien faire directement sur le modèle.)

- [ ] **Step 5: Enregistrer le fichier de sécurité dans le manifest**

Modifier `odoo-addons/haccp_report/__manifest__.py` — `data` (ajouter avant `data/haccp_dlc_ouverture_sequence.xml`) :

```python
    'data': [
        'security/ir.model.access.csv',
        'security/haccp_kitchen_security.xml',
        'data/haccp_dlc_ouverture_sequence.xml',
        'report/report_action.xml',
        'report/report_template.xml',
        'views/haccp_report_views.xml',
        'views/haccp_calculs_views.xml',
        'views/haccp_document_views.xml',
        'views/menu.xml',
        'views/quality_inherit.xml',
    ],
```

- [ ] **Step 6: Mettre à jour et lancer les tests**

Run: `./scripts/deploy-haccp-report.sh --update` puis `./scripts/deploy-haccp-report.sh --test`
Expected: tous les tests passent, y compris les deux nouveaux tests de sécurité (qui confirment l'`AccessError`).

- [ ] **Step 7: Commit**

```bash
git add odoo-addons/haccp_report/security/haccp_kitchen_security.xml odoo-addons/haccp_report/security/ir.model.access.csv odoo-addons/haccp_report/__manifest__.py odoo-addons/haccp_report/tests/test_haccp_dlc_ouverture_security.py odoo-addons/haccp_report/tests/__init__.py
git commit -m "feat(haccp): groupe portail cuisine sans accès ACL direct + tests de sécurité"
```

---

## Task 4: Générateur et envoi ZPL

Fonctions pures, aucune dépendance ORM — testables sans base de données.

**Files:**
- Create: `odoo-addons/haccp_report/models/zpl_printer.py`
- Modify: `odoo-addons/haccp_report/models/__init__.py`
- Test: `odoo-addons/haccp_report/tests/test_zpl_printer.py`

- [ ] **Step 1: Écrire les tests (RED)**

```python
# odoo-addons/haccp_report/tests/test_zpl_printer.py
import socket
import unittest
from unittest.mock import MagicMock, patch

from odoo.addons.haccp_report.models.zpl_printer import build_zpl, send_zpl


class TestBuildZpl(unittest.TestCase):
    def test_contains_product_name_and_reference(self):
        zpl = build_zpl(
            reference='2026-200-014',
            product_name='Sauce tomate maison',
            date_ouverture='19/07/2026',
            operateur_name='M. Dupont',
            date_limite='22/07/2026',
            duree_jours=3,
            condition_label='Réfrigéré (+4°C)',
            portal_url='http://192.168.1.182:8029/haccp/etiquette/42/abc123',
        )
        self.assertTrue(zpl.startswith('^XA'))
        self.assertTrue(zpl.rstrip().endswith('^XZ'))
        self.assertIn('Sauce tomate maison', zpl)
        self.assertIn('2026-200-014', zpl)
        self.assertIn('22/07/2026', zpl)
        self.assertIn('http://192.168.1.182:8029/haccp/etiquette/42/abc123', zpl)


class TestSendZpl(unittest.TestCase):
    def test_returns_error_when_printer_ip_not_configured(self):
        ok, error = send_zpl('^XA^XZ', printer_ip=None)
        self.assertFalse(ok)
        self.assertIn('non configurée', error)

    @patch('socket.create_connection')
    def test_sends_zpl_bytes_over_socket(self, mock_create_connection):
        mock_sock = MagicMock()
        mock_create_connection.return_value.__enter__.return_value = mock_sock

        ok, error = send_zpl('^XA^XZ', printer_ip='192.168.1.50', port=9100, timeout=3)

        self.assertTrue(ok)
        self.assertIsNone(error)
        mock_create_connection.assert_called_once_with(('192.168.1.50', 9100), timeout=3)
        mock_sock.sendall.assert_called_once_with(b'^XA^XZ')

    @patch('socket.create_connection')
    def test_returns_error_on_connection_failure(self, mock_create_connection):
        mock_create_connection.side_effect = OSError('Connection refused')

        ok, error = send_zpl('^XA^XZ', printer_ip='192.168.1.50')

        self.assertFalse(ok)
        self.assertEqual(error, 'Connection refused')


if __name__ == '__main__':
    unittest.main()
```

Ajouter l'import dans `odoo-addons/haccp_report/tests/__init__.py` :

```python
from . import test_haccp_report
from . import test_haccp_calculs
from . import test_haccp_document
from . import test_haccp_dlc_ouverture
from . import test_haccp_dlc_ouverture_security
from . import test_zpl_printer
```

- [ ] **Step 2: Vérifier que les tests échouent**

Run: `./scripts/deploy-haccp-report.sh --test`
Expected: échec — `odoo.addons.haccp_report.models.zpl_printer` n'existe pas (`ModuleNotFoundError`/`ImportError`).

- [ ] **Step 3: Implémenter**

```python
# odoo-addons/haccp_report/models/zpl_printer.py
import socket


def build_zpl(reference, product_name, date_ouverture, operateur_name,
               date_limite, duree_jours, condition_label, portal_url):
    """Construit le ZPL pour l'étiquette DLC secondaire (format 62x38mm,
    imprimante OXHOO TLP200 compatible Zebra ZPL)."""
    return (
        '^XA\n'
        '^CF0,30\n'
        f'^FO20,20^FD{product_name}^FS\n'
        '^CF0,20\n'
        f'^FO20,60^FDOuvert: {date_ouverture}  Par: {operateur_name}^FS\n'
        '^FO20,90^GB300,40,2^FS\n'
        '^CF0,28\n'
        f'^FO30,100^FDDLC: {date_limite} (J+{duree_jours})^FS\n'
        f'^FO20,150^FDConservation: {condition_label}^FS\n'
        f'^BY2^FO20,180^BCN,50,Y,N,N^FD{reference}^FS\n'
        f'^FO250,150^BQN,2,4^FDQA,{portal_url}^FS\n'
        '^XZ\n'
    )


def send_zpl(zpl_text, printer_ip, port=9100, timeout=3):
    """Envoie le ZPL brut à l'imprimante réseau. Retourne (ok, error)."""
    if not printer_ip:
        return False, (
            "Adresse IP imprimante non configurée "
            "(paramètre système haccp_report.zebra_printer_ip)"
        )
    try:
        with socket.create_connection((printer_ip, port), timeout=timeout) as sock:
            sock.sendall(zpl_text.encode('utf-8'))
        return True, None
    except OSError as exc:
        return False, str(exc)
```

- [ ] **Step 4: Enregistrer le module**

Modifier `odoo-addons/haccp_report/models/__init__.py` (ajouter `zpl_printer`, ordre indifférent car pas de dépendance croisée) :

```python
from . import haccp_report
from . import report_renderer
from . import haccp_dlc_table
from . import haccp_dlc
from . import haccp_dlc_ouverture
from . import haccp_refroidissement
from . import haccp_dilution
from . import haccp_decongelation
from . import haccp_reassort
from . import haccp_document
from . import zpl_printer
```

- [ ] **Step 5: Lancer les tests**

Run: `./scripts/deploy-haccp-report.sh --test`
Expected: tous les tests de `test_zpl_printer.py` passent.

- [ ] **Step 6: Commit**

```bash
git add odoo-addons/haccp_report/models/zpl_printer.py odoo-addons/haccp_report/models/__init__.py odoo-addons/haccp_report/tests/test_zpl_printer.py odoo-addons/haccp_report/tests/__init__.py
git commit -m "feat(haccp): générateur ZPL + envoi réseau pour étiquettes DLC"
```

---

## Task 5: Contrôleur et template — création d'étiquette

Formulaire GET (aperçu DLC sans JS, via `formmethod="get"` par défaut) et soumission POST (création + impression).

**Files:**
- Create: `odoo-addons/haccp_report/controllers/__init__.py`
- Create: `odoo-addons/haccp_report/controllers/haccp_portal.py`
- Create: `odoo-addons/haccp_report/views/haccp_portal_templates.xml`
- Modify: `odoo-addons/haccp_report/__init__.py`
- Modify: `odoo-addons/haccp_report/__manifest__.py`

- [ ] **Step 1: Créer le package des contrôleurs**

```python
# odoo-addons/haccp_report/controllers/__init__.py
from . import haccp_portal
```

- [ ] **Step 2: Écrire le contrôleur (formulaire + soumission)**

```python
# odoo-addons/haccp_report/controllers/haccp_portal.py
import logging
from datetime import timedelta

from odoo import fields, http, _
from odoo.http import request
from werkzeug.exceptions import Forbidden, NotFound

from odoo.addons.haccp_report.models.haccp_dlc_table import (
    DLC_TABLE, DLC_FAMILLE_SELECTION, DLC_CONDITION_SELECTION,
)
from odoo.addons.haccp_report.models.zpl_printer import build_zpl, send_zpl

_logger = logging.getLogger(__name__)


class HaccpPortalController(http.Controller):

    def _check_kitchen_group(self):
        if request.env.user._is_public() or not request.env.user.has_group(
            'haccp_report.group_haccp_kitchen'
        ):
            raise Forbidden()

    def _get_record_or_404(self, ouverture_id, access_token):
        record = request.env['haccp.dlc.ouverture'].sudo().browse(ouverture_id)
        if not record.exists() or not record.access_token or record.access_token != access_token:
            raise NotFound()
        return record

    @http.route('/haccp/etiquette/nouvelle', type='http', auth='user', methods=['GET'], csrf=False)
    def haccp_etiquette_form(self, error=None, **kwargs):
        self._check_kitchen_group()
        products = request.env['product.template'].sudo().search(
            [('categ_id.name', '=', 'Alimentaire')], limit=200
        )
        famille = kwargs.get('famille') or 'autre'
        condition = kwargs.get('condition') or 'refrigere'
        duree_jours = DLC_TABLE.get((famille, condition), 0)
        date_ouverture = kwargs.get('date_ouverture') or fields.Date.today().isoformat()
        date_limite = None
        if duree_jours:
            date_limite = (
                fields.Date.from_string(date_ouverture) + timedelta(days=duree_jours)
            ).isoformat()

        return request.render('haccp_report.portal_etiquette_form', {
            'products': products,
            'famille_options': DLC_FAMILLE_SELECTION,
            'condition_options': DLC_CONDITION_SELECTION,
            'famille': famille,
            'condition': condition,
            'date_ouverture': date_ouverture,
            'product_name': kwargs.get('product_name', ''),
            'selected_product_id': int(kwargs['product_id']) if kwargs.get('product_id') else False,
            'duree_jours': duree_jours,
            'date_limite': date_limite,
            'user_name': request.env.user.name,
            'error': error,
            'csrf_token': request.csrf_token(),
        })

    @http.route('/haccp/etiquette/nouvelle', type='http', auth='user', methods=['POST'], csrf=True)
    def haccp_etiquette_submit(self, **post):
        self._check_kitchen_group()

        product_id = int(post['product_id']) if post.get('product_id') else False
        product_name = post.get('product_name') or ''
        if product_id:
            product_name = request.env['product.template'].sudo().browse(product_id).name

        if not product_name or not post.get('famille') or not post.get('condition'):
            return self.haccp_etiquette_form(
                error=_('Merci de renseigner le produit, la famille et la condition.'),
                **post,
            )

        record = request.env['haccp.dlc.ouverture'].sudo().create({
            'product_id': product_id,
            'product_name': product_name,
            'famille': post['famille'],
            'condition': post['condition'],
            'date_ouverture': post.get('date_ouverture') or fields.Datetime.now(),
            'operateur_id': request.env.user.id,
        })

        return self._print_and_render(record)

    def _print_and_render(self, record):
        printer_ip = request.env['ir.config_parameter'].sudo().get_param(
            'haccp_report.zebra_printer_ip'
        )
        portal_url = request.httprequest.host_url.rstrip('/') + record.access_url
        zpl = build_zpl(
            reference=record.reference,
            product_name=record.product_name,
            date_ouverture=record.date_ouverture,
            operateur_name=record.operateur_id.name,
            date_limite=record.date_limite,
            duree_jours=record.duree_jours,
            condition_label=dict(DLC_CONDITION_SELECTION).get(record.condition, record.condition),
            portal_url=portal_url,
        )
        ok, error = send_zpl(zpl, printer_ip)
        return request.render('haccp_report.portal_etiquette_confirmation', {
            'record': record, 'print_ok': ok, 'print_error': error,
            'csrf_token': request.csrf_token(),
        })

    @http.route(
        '/haccp/etiquette/<int:ouverture_id>/<string:access_token>/reessayer',
        type='http', auth='user', methods=['POST'], csrf=True,
    )
    def haccp_etiquette_reessayer(self, ouverture_id, access_token, **post):
        self._check_kitchen_group()
        record = self._get_record_or_404(ouverture_id, access_token)
        return self._print_and_render(record)
```

- [ ] **Step 3: Créer les templates QWeb (formulaire + confirmation)**

```xml
<!-- odoo-addons/haccp_report/views/haccp_portal_templates.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <template id="portal_etiquette_form" name="Nouvelle étiquette DLC">
    <!DOCTYPE html>
    <html lang="fr">
      <head>
        <meta charset="utf-8"/>
        <title>Nouvelle étiquette DLC</title>
        <style>
          body { font-family: -apple-system, Arial, sans-serif; max-width: 420px; margin: 20px auto; padding: 0 16px; color: #111; }
          .f-label { font-size: 12px; text-transform: uppercase; color: #666; margin-top: 14px; }
          select, input { width: 100%; box-sizing: border-box; padding: 8px; font-size: 15px; border: 1px solid #ccc; border-radius: 6px; margin-top: 4px; }
          .dlc-preview { margin-top: 16px; padding: 10px; border-radius: 6px; background: #eaf7ea; border: 1px solid #2c5f2d; color: #1e4620; text-align: center; font-weight: bold; }
          .btn { margin-top: 16px; width: 100%; padding: 12px; border: none; border-radius: 6px; font-size: 15px; font-weight: bold; }
          .btn-preview { background: #eee; color: #333; }
          .btn-print { background: #2c5f2d; color: #fff; }
          .error { color: #b3261e; margin-top: 10px; }
        </style>
      </head>
      <body>
        <h2>Nouvelle étiquette DLC</h2>
        <p t-esc="'Connecté : %s' % user_name"/>
        <t t-if="error">
          <p class="error" t-esc="error"/>
        </t>
        <form method="get" action="/haccp/etiquette/nouvelle">
          <input type="hidden" name="csrf_token" t-att-value="csrf_token"/>

          <div class="f-label">Produit</div>
          <select name="product_id">
            <option value="">— Autre (saisie libre) —</option>
            <t t-foreach="products" t-as="product">
              <option t-att-value="product.id" t-att-selected="product.id == selected_product_id">
                <t t-esc="product.name"/>
              </option>
            </t>
          </select>
          <div class="f-label">Nom du produit (si "Autre")</div>
          <input type="text" name="product_name" t-att-value="product_name"/>

          <div class="f-label">Famille</div>
          <select name="famille">
            <t t-foreach="famille_options" t-as="opt">
              <option t-att-value="opt[0]" t-att-selected="opt[0] == famille">
                <t t-esc="opt[1]"/>
              </option>
            </t>
          </select>

          <div class="f-label">Condition de conservation</div>
          <select name="condition">
            <t t-foreach="condition_options" t-as="opt">
              <option t-att-value="opt[0]" t-att-selected="opt[0] == condition">
                <t t-esc="opt[1]"/>
              </option>
            </t>
          </select>

          <div class="f-label">Date d'ouverture</div>
          <input type="date" name="date_ouverture" t-att-value="date_ouverture"/>

          <t t-if="duree_jours">
            <div class="dlc-preview">
              DLC calculée : <t t-esc="date_limite"/> (J+<t t-esc="duree_jours"/>)
            </div>
          </t>

          <button type="submit" class="btn btn-preview">Actualiser l'aperçu</button>
          <button type="submit" formmethod="post" class="btn btn-print">🖨 Imprimer l'étiquette</button>
        </form>
      </body>
    </html>
  </template>

  <template id="portal_etiquette_confirmation" name="Étiquette imprimée">
    <!DOCTYPE html>
    <html lang="fr">
      <head><meta charset="utf-8"/><title>Étiquette DLC</title></head>
      <body style="font-family: -apple-system, Arial, sans-serif; max-width: 420px; margin: 20px auto; padding: 0 16px; color:#111;">
        <h2>Étiquette DLC — <t t-esc="record.reference"/></h2>
        <t t-if="print_ok">
          <p style="color:#1e7d32; font-weight:bold;">✓ Étiquette envoyée à l'imprimante cuisine</p>
        </t>
        <t t-if="not print_ok">
          <p style="color:#b3261e; font-weight:bold;">✗ Échec d'impression : <t t-esc="print_error"/></p>
          <form method="post" t-attf-action="/haccp/etiquette/#{record.id}/#{record.access_token}/reessayer">
            <input type="hidden" name="csrf_token" t-att-value="csrf_token"/>
            <button type="submit">Réessayer l'impression</button>
          </form>
        </t>
        <p>
          Produit : <t t-esc="record.product_name"/><br/>
          DLC : <t t-esc="record.date_limite"/>
        </p>
        <a href="/haccp/etiquette/nouvelle">Nouvelle étiquette</a>
      </body>
    </html>
  </template>
</odoo>
```

- [ ] **Step 4: Enregistrer contrôleur et template**

Modifier `odoo-addons/haccp_report/__init__.py` pour charger les contrôleurs :

```python
from . import models
from . import controllers
```

Modifier `odoo-addons/haccp_report/__manifest__.py` — `data` (ajouter le template) :

```python
    'data': [
        'security/ir.model.access.csv',
        'security/haccp_kitchen_security.xml',
        'data/haccp_dlc_ouverture_sequence.xml',
        'report/report_action.xml',
        'report/report_template.xml',
        'views/haccp_report_views.xml',
        'views/haccp_calculs_views.xml',
        'views/haccp_document_views.xml',
        'views/haccp_portal_templates.xml',
        'views/menu.xml',
        'views/quality_inherit.xml',
    ],
```

- [ ] **Step 5: Déployer et vérifier manuellement**

Run: `./scripts/deploy-haccp-report.sh --update`
Puis créer un utilisateur portail de test avec le groupe `HACCP — Cuisine (portail)` (Réglages > Utilisateurs, ou via `odoo shell`), se connecter, ouvrir `http://192.168.1.182:8029/haccp/etiquette/nouvelle`.
Expected: le formulaire s'affiche, "Actualiser l'aperçu" met à jour la DLC calculée, "Imprimer l'étiquette" crée l'enregistrement (visible en base même si l'imprimante n'est pas encore configurée — `print_ok` sera `False` avec le message "non configurée", ce qui est le comportement attendu tant que Task 8 n'a pas réglé `haccp_report.zebra_printer_ip`).

- [ ] **Step 6: Commit**

```bash
git add odoo-addons/haccp_report/controllers odoo-addons/haccp_report/views/haccp_portal_templates.xml odoo-addons/haccp_report/__init__.py odoo-addons/haccp_report/__manifest__.py
git commit -m "feat(haccp): portail cuisine — formulaire de création d'étiquette DLC"
```

---

## Task 6: Contrôleur et template — consultation publique + clôture

**Files:**
- Modify: `odoo-addons/haccp_report/controllers/haccp_portal.py`
- Modify: `odoo-addons/haccp_report/views/haccp_portal_templates.xml`

- [ ] **Step 1: Ajouter les routes de consultation et de clôture**

Ajouter à la fin de la classe `HaccpPortalController` dans `odoo-addons/haccp_report/controllers/haccp_portal.py` :

```python
    @http.route(
        '/haccp/etiquette/<int:ouverture_id>/<string:access_token>',
        type='http', auth='public', methods=['GET'],
    )
    def haccp_etiquette_view(self, ouverture_id, access_token, **kwargs):
        record = self._get_record_or_404(ouverture_id, access_token)
        can_close = (
            not request.env.user._is_public()
            and request.env.user.has_group('haccp_report.group_haccp_kitchen')
        )
        return request.render('haccp_report.portal_etiquette_view', {
            'record': record,
            'can_close': can_close,
            'csrf_token': request.csrf_token(),
        })

    @http.route(
        '/haccp/etiquette/<int:ouverture_id>/<string:access_token>/cloturer',
        type='http', auth='user', methods=['POST'], csrf=True,
    )
    def haccp_etiquette_cloturer(self, ouverture_id, access_token, statut, **post):
        self._check_kitchen_group()
        record = self._get_record_or_404(ouverture_id, access_token)
        record.action_cloturer(statut)
        return request.redirect('/haccp/etiquette/%s/%s' % (ouverture_id, access_token))
```

- [ ] **Step 2: Ajouter le template de consultation**

Ajouter dans `odoo-addons/haccp_report/views/haccp_portal_templates.xml`, avant `</odoo>` :

```xml
  <template id="portal_etiquette_view" name="Fiche étiquette DLC">
    <!DOCTYPE html>
    <html lang="fr">
      <head><meta charset="utf-8"/><title>Fiche DLC</title></head>
      <body style="font-family: -apple-system, Arial, sans-serif; max-width: 420px; margin: 20px auto; padding: 0 16px; text-align:center; color:#111;">
        <h2>Fiche DLC — <t t-esc="record.product_name"/></h2>
        <p>
          <t t-if="record.statut == 'ouvert' and not record.est_expire">
            <span style="color:#1e7d32; font-weight:bold;">✓ Valide</span>
          </t>
          <t t-if="record.statut == 'ouvert' and record.est_expire">
            <span style="color:#b3261e; font-weight:bold;">⚠ Expiré</span>
          </t>
          <t t-if="record.statut == 'termine'">
            <span style="color:#555; font-weight:bold;">Terminé</span>
          </t>
          <t t-if="record.statut == 'jete'">
            <span style="color:#555; font-weight:bold;">Jeté</span>
          </t>
        </p>
        <div style="text-align:left; font-size:14px; line-height:1.6;">
          Référence : <t t-esc="record.reference"/><br/>
          Ouvert le : <t t-esc="record.date_ouverture"/><br/>
          Par : <t t-esc="record.operateur_id.name"/><br/>
          DLC : <t t-esc="record.date_limite"/>
        </div>
        <t t-if="can_close and record.statut == 'ouvert'">
          <form method="post" t-attf-action="/haccp/etiquette/#{record.id}/#{record.access_token}/cloturer">
            <input type="hidden" name="csrf_token" t-att-value="csrf_token"/>
            <button type="submit" name="statut" value="termine" style="background:#2c5f2d;color:#fff;padding:10px;border:none;border-radius:6px;width:100%;margin-top:14px;">Marquer terminé</button>
            <button type="submit" name="statut" value="jete" style="background:#b3261e;color:#fff;padding:10px;border:none;border-radius:6px;width:100%;margin-top:8px;">Marquer jeté</button>
          </form>
        </t>
        <t t-if="not can_close and record.statut == 'ouvert'">
          <p style="font-size:12px;color:#666;margin-top:14px;">Connecte-toi avec un compte cuisine pour clôturer cette étiquette.</p>
        </t>
      </body>
    </html>
  </template>
```

- [ ] **Step 3: Déployer et vérifier manuellement**

Run: `./scripts/deploy-haccp-report.sh --update`
Ouvrir l'URL `access_url` d'un enregistrement créé à la Task 5 (ex. `http://192.168.1.182:8029/haccp/etiquette/1/<token>` — récupérer le token via `odoo shell` ou l'écran de confirmation).
Expected : la fiche s'affiche sans connexion (lecture publique) ; connecté avec le compte cuisine, les boutons "Marquer terminé"/"Marquer jeté" apparaissent et fonctionnent (redirection vers la même page avec le nouveau statut affiché).

- [ ] **Step 4: Commit**

```bash
git add odoo-addons/haccp_report/controllers/haccp_portal.py odoo-addons/haccp_report/views/haccp_portal_templates.xml
git commit -m "feat(haccp): portail cuisine — fiche de consultation publique + clôture"
```

---

## Task 7: Tests de sécurité du contrôleur

Vérifie par des tests automatisés (`HttpCase`) les garanties de sécurité décrites dans la spec §7 : accès refusé sans le groupe, `operateur_id` toujours forcé serveur, token invalide → 404, lecture publique sans connexion, clôture refusée si non connecté.

**Files:**
- Test: `odoo-addons/haccp_report/tests/test_haccp_portal_controller.py`
- Modify: `odoo-addons/haccp_report/tests/__init__.py`

- [ ] **Step 1: Écrire les tests (RED)**

```python
# odoo-addons/haccp_report/tests/test_haccp_portal_controller.py
from odoo import fields
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestHaccpPortalController(HttpCase):

    def setUp(self):
        super().setUp()
        self.kitchen_user = self.env['res.users'].create({
            'name': 'Cuisinier Test',
            'login': 'cuisinier.controller@example.com',
            'password': 'cuisinier123',
            'groups_id': [(6, 0, [
                self.env.ref('base.group_portal').id,
                self.env.ref('haccp_report.group_haccp_kitchen').id,
            ])],
        })
        self.plain_portal_user = self.env['res.users'].create({
            'name': 'Portail sans cuisine',
            'login': 'portail.simple@example.com',
            'password': 'portail123',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })

    def test_formulaire_refuse_sans_groupe_cuisine(self):
        self.authenticate('portail.simple@example.com', 'portail123')
        response = self.url_open('/haccp/etiquette/nouvelle')
        self.assertEqual(response.status_code, 403)

    def test_creation_force_operateur_depuis_session(self):
        self.authenticate('cuisinier.controller@example.com', 'cuisinier123')
        autre_utilisateur = self.env['res.users'].create({
            'name': 'Un Autre',
            'login': 'un.autre@example.com',
        })
        self.url_open('/haccp/etiquette/nouvelle', data={
            'csrf_token': self._get_csrf_token(),
            'product_name': 'Test création',
            'famille': 'autre',
            'condition': 'refrigere',
            'date_ouverture': fields.Datetime.now(),
            'operateur_id': autre_utilisateur.id,  # tentative d'usurpation
        })
        record = self.env['haccp.dlc.ouverture'].search(
            [('product_name', '=', 'Test création')], limit=1
        )
        self.assertTrue(record)
        self.assertEqual(record.operateur_id, self.kitchen_user)

    def test_fiche_publique_lisible_sans_connexion(self):
        record = self.env['haccp.dlc.ouverture'].create({
            'product_name': 'Fiche publique',
            'famille': 'autre',
            'condition': 'refrigere',
            'date_ouverture': fields.Datetime.now(),
            'operateur_id': self.kitchen_user.id,
        })
        response = self.url_open(record.access_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Fiche publique', response.text)

    def test_token_invalide_renvoie_404(self):
        record = self.env['haccp.dlc.ouverture'].create({
            'product_name': 'Test 404',
            'famille': 'autre',
            'condition': 'refrigere',
            'date_ouverture': fields.Datetime.now(),
            'operateur_id': self.kitchen_user.id,
        })
        response = self.url_open('/haccp/etiquette/%s/mauvais-token' % record.id)
        self.assertEqual(response.status_code, 404)

    def test_cloture_refusee_sans_connexion(self):
        record = self.env['haccp.dlc.ouverture'].create({
            'product_name': 'Test clôture',
            'famille': 'autre',
            'condition': 'refrigere',
            'date_ouverture': fields.Datetime.now(),
            'operateur_id': self.kitchen_user.id,
        })
        response = self.url_open(
            '%s/cloturer' % record.access_url, data={'statut': 'termine'}
        )
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(record.statut, 'ouvert')

    def _get_csrf_token(self):
        response = self.url_open('/haccp/etiquette/nouvelle')
        import re
        match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
        return match.group(1) if match else ''
```

Ajouter l'import dans `odoo-addons/haccp_report/tests/__init__.py` :

```python
from . import test_haccp_report
from . import test_haccp_calculs
from . import test_haccp_document
from . import test_haccp_dlc_ouverture
from . import test_haccp_dlc_ouverture_security
from . import test_zpl_printer
from . import test_haccp_portal_controller
```

- [ ] **Step 2: Vérifier que les tests échouent (ou passent déjà si l'implémentation des Tasks 5-6 est correcte)**

Run: `./scripts/deploy-haccp-report.sh --test`
Expected: si les Tasks 5 et 6 ont été correctement implémentées, ces tests devraient déjà passer — ce sont des tests de non-régression sur le comportement de sécurité déjà codé. S'il y a un échec, il révèle un bug dans le contrôleur (ex. `operateur_id` non forcé, route de clôture mal protégée) : corriger le contrôleur, pas le test.

- [ ] **Step 3: Corriger si besoin, puis confirmer que tout passe**

Run: `./scripts/deploy-haccp-report.sh --test`
Expected: tous les tests passent, y compris `test_haccp_portal_controller.py`.

- [ ] **Step 4: Commit**

```bash
git add odoo-addons/haccp_report/tests/test_haccp_portal_controller.py odoo-addons/haccp_report/tests/__init__.py
git commit -m "test(haccp): couverture sécurité du contrôleur portail (HttpCase)"
```

---

## Task 8: Déploiement et vérification manuelle avec l'imprimante réelle

Pas de TDD ici — vérification humaine en conditions réelles avec le matériel OXHOO TLP200, non automatisable en CI (même approche que pour l'intégration TTN, cf. mémoire `project-demo-simulate-sensor`).

**Files:** aucun changement de code.

- [ ] **Step 1: Configurer l'adresse IP de l'imprimante**

Dans Odoo : Réglages > Technique > Paramètres > Paramètres système (mode développeur activé), créer la clé `haccp_report.zebra_printer_ip` avec l'adresse IP réseau de l'OXHOO TLP200.

- [ ] **Step 2: Créer un compte cuisine réel**

Réglages > Utilisateurs > Nouveau, type "Portail", assigner le groupe "HACCP — Cuisine (portail)", envoyer l'invitation ou définir un mot de passe.

- [ ] **Step 3: Créer un produit de test dans la catégorie "Alimentaire"**

Si la catégorie "Alimentaire" n'existe pas encore dans `product.category`, la créer, et y rattacher au moins un produit de test — sinon la liste déroulante du formulaire sera vide (le champ "Autre" reste toujours utilisable en repli).

- [ ] **Step 4: Test bout en bout avec impression réelle**

Se connecter avec le compte cuisine sur une tablette/PC du réseau, aller sur `/haccp/etiquette/nouvelle`, remplir le formulaire, cliquer "Imprimer l'étiquette".
Expected: l'étiquette sort physiquement sur l'OXHOO TLP200 avec le bon contenu (produit, DLC, code-barres, QR).

- [ ] **Step 5: Scanner le QR et clôturer**

Scanner le QR de l'étiquette imprimée avec un téléphone, vérifier que la fiche s'affiche, se connecter avec le compte cuisine, cliquer "Marquer terminé".
Expected: la fiche affiche "Terminé" après rafraîchissement.

- [ ] **Step 6: Mettre à jour la mémoire du projet**

Documenter dans la mémoire (`project-haccp-methode-menu` ou nouvelle entrée) : l'IP configurée, le login du compte cuisine de test, et toute surprise rencontrée avec l'imprimante réelle (ex. format d'étiquette à ajuster, orientation, etc.).
