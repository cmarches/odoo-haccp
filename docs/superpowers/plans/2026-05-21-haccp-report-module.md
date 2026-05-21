# Module `haccp_report` — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Créer le module Odoo `haccp_report` qui génère un rapport PDF HACCP DDPP (6 sections réglementaires) depuis les données IoT quality.check/alert, avec historique persistant et accès via wizard date_start/date_end.

**Architecture:** Modèle persistant `haccp.report` (date_start, date_end, responsible_id, state). AbstractModel renderer `report.haccp_report.report_haccp_ddpp` qui requête quality.point/check/alert et injecte stats calculés dans un template QWeb 6 sections. Deux points d'entrée : menu Qualité > Rapports + bouton dans quality.check list view.

**Tech Stack:** Odoo 19 EE (dev : 192.168.1.182:8029, base odoo19e_dev) / CE (prod), Python 3, QWeb XML, WeasyPrint PDF, Docker (`odoo19e_app`)

---

## Informations de déploiement

| Élément | Valeur |
|---------|--------|
| Serveur dev | `192.168.1.182` (SSH : `christian@192.168.1.182`) |
| Container Odoo EE | `odoo19e_app` |
| Addons custom (host) | `/home/christian/odoo-multiversion/v19e/addons/` |
| Addons custom (container) | `/mnt/extra-addons/` |
| Addons path container CMD | `/mnt/enterprise-addons,/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons` |
| Base de données | `odoo19e_dev` |
| Repo local | `odoo-addons/haccp_report/` → rsync vers serveur |

## Champs Odoo vérifiés

| Modèle | Champ | Type | Valeur pour IoT |
|--------|-------|------|-----------------|
| `quality.check` | `measure` | Float | valeur mesurée |
| `quality.check` | `quality_state` | Selection | `'pass'` / `'fail'` |
| `quality.check` | `create_date` | Datetime | date de la mesure |
| `quality.check` | `point_id` | Many2one | CCP lié |
| `quality.check` | `tolerance_min/max` | Float related | seuils (via point) |
| `quality.check` | `norm_unit` | Char related | unité (°C, %) |
| `quality.point` | `name` | Char | nom du CCP |
| `quality.point` | `title` | Char | sous-titre (optionnel) |
| `quality.point` | `tolerance_min/max` | Float | limites critiques |
| `quality.point` | `norm_unit` | Char | unité |
| `quality.alert` | `action_corrective` | Html | action corrective |
| `quality.alert` | `date_assign` | Datetime | date ouverture |
| `quality.alert` | `date_close` | Datetime | date clôture |
| `quality.alert` | `stage_id.done` | Boolean | alerte clôturée si True |
| `quality.alert` | `check_id` | Many2one | check lié |

---

## Carte des fichiers

```
odoo-addons/haccp_report/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── haccp_report.py          ← modèle persistant
│   └── report_renderer.py       ← AbstractModel + _get_report_values()
├── report/
│   ├── report_action.xml        ← ir.actions.report
│   └── report_template.xml      ← QWeb 6 sections
├── views/
│   ├── haccp_report_views.xml   ← form view + list view
│   ├── menu.xml                 ← Qualité > Rapports
│   └── quality_inherit.xml      ← bouton dans quality.check list
├── security/
│   └── ir.model.access.csv
└── tests/
    ├── __init__.py
    └── test_haccp_report.py

scripts/
└── deploy-haccp-report.sh       ← rsync + restart
```

---

## Task 1 : Scaffold du module + script de déploiement

**Files:**
- Create: `odoo-addons/haccp_report/__manifest__.py`
- Create: `odoo-addons/haccp_report/__init__.py`
- Create: `odoo-addons/haccp_report/models/__init__.py`
- Create: `odoo-addons/haccp_report/report/.gitkeep`
- Create: `odoo-addons/haccp_report/views/.gitkeep`
- Create: `odoo-addons/haccp_report/security/.gitkeep`
- Create: `odoo-addons/haccp_report/tests/__init__.py`
- Create: `scripts/deploy-haccp-report.sh`

- [ ] **Step 1 : Créer l'arborescence du module**

```bash
mkdir -p odoo-addons/haccp_report/{models,report,views,security,tests}
touch odoo-addons/haccp_report/report/.gitkeep
touch odoo-addons/haccp_report/views/.gitkeep
touch odoo-addons/haccp_report/security/.gitkeep
```

- [ ] **Step 2 : Écrire `__manifest__.py`**

```python
# odoo-addons/haccp_report/__manifest__.py
{
    'name': 'Rapport HACCP DDPP',
    'version': '19.0.1.0.0',
    'summary': 'Rapport PDF réglementaire HACCP pour contrôles DDPP',
    'category': 'Quality',
    'author': 'AIFluence Digital',
    'depends': ['quality_control', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'report/report_action.xml',
        'report/report_template.xml',
        'views/haccp_report_views.xml',
        'views/menu.xml',
        'views/quality_inherit.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
```

- [ ] **Step 3 : Écrire `__init__.py` et `models/__init__.py`**

```python
# odoo-addons/haccp_report/__init__.py
from . import models
```

```python
# odoo-addons/haccp_report/models/__init__.py
from . import haccp_report
from . import report_renderer
```

```python
# odoo-addons/haccp_report/tests/__init__.py
from . import test_haccp_report
```

- [ ] **Step 4 : Écrire le script de déploiement**

```bash
#!/bin/bash
# scripts/deploy-haccp-report.sh
# Usage: ./scripts/deploy-haccp-report.sh [--install|--update|--test]

set -e

SERVER="christian@192.168.1.182"
REMOTE_ADDONS="/home/christian/odoo-multiversion/v19e/addons"
LOCAL_MODULE="odoo-addons/haccp_report"
CONTAINER="odoo19e_app"
DB="odoo19e_dev"
ADDONS_PATH="/mnt/enterprise-addons,/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons"

echo "==> Sync module vers serveur..."
rsync -av --delete "$LOCAL_MODULE/" "$SERVER:$REMOTE_ADDONS/haccp_report/"

MODE="${1:---update}"

if [ "$MODE" = "--install" ]; then
    echo "==> Installation du module (première fois)..."
    ssh "$SERVER" "docker exec $CONTAINER odoo -d $DB -i haccp_report --stop-after-init --addons-path='$ADDONS_PATH' --no-http"
elif [ "$MODE" = "--update" ]; then
    echo "==> Mise à jour du module..."
    ssh "$SERVER" "docker exec $CONTAINER odoo -d $DB -u haccp_report --stop-after-init --addons-path='$ADDONS_PATH' --no-http"
elif [ "$MODE" = "--test" ]; then
    echo "==> Lancement des tests..."
    ssh "$SERVER" "docker exec $CONTAINER odoo -d $DB --test-enable -i haccp_report --stop-after-init --addons-path='$ADDONS_PATH' --no-http"
fi

echo "==> Done."
```

```bash
chmod +x scripts/deploy-haccp-report.sh
```

- [ ] **Step 5 : Commit**

```bash
git add odoo-addons/ scripts/deploy-haccp-report.sh
git commit -m "feat(haccp_report): scaffold module + deploy script"
```

---

## Task 2 : Modèle persistant `haccp.report`

**Files:**
- Create: `odoo-addons/haccp_report/models/haccp_report.py`
- Create: `odoo-addons/haccp_report/tests/test_haccp_report.py`

- [ ] **Step 1 : Écrire le test en échec**

```python
# odoo-addons/haccp_report/tests/test_haccp_report.py
from datetime import date, timedelta
from odoo.tests.common import TransactionCase


class TestHaccpReport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.point = cls.env['quality.point'].create({
            'name': 'TEST-Frigo',
            'tolerance_min': -30.0,
            'tolerance_max': 4.0,
            'norm_unit': '°C',
        })
        cls.today = date.today()
        cls.date_start = cls.today - timedelta(days=7)
        cls.date_end = cls.today

        # 9 checks conformes, 1 non-conforme
        for _ in range(9):
            cls.env['quality.check'].create({
                'point_id': cls.point.id,
                'measure': 2.5,
                'quality_state': 'pass',
            })
        cls.failing_check = cls.env['quality.check'].create({
            'point_id': cls.point.id,
            'measure': 5.8,
            'quality_state': 'fail',
        })
        cls.alert = cls.env['quality.alert'].create({
            'title': 'Alerte test frigo',
            'check_id': cls.failing_check.id,
            'action_corrective': '<p>Vérification joint de porte</p>',
        })

    def test_name_computed(self):
        report = self.env['haccp.report'].create({
            'date_start': self.date_start,
            'date_end': self.date_end,
        })
        start_str = self.date_start.strftime('%d/%m/%Y')
        end_str = self.date_end.strftime('%d/%m/%Y')
        self.assertEqual(
            report.name,
            f'Rapport HACCP DDPP – {start_str} → {end_str}',
        )

    def test_check_count(self):
        report = self.env['haccp.report'].create({
            'date_start': self.date_start,
            'date_end': self.date_end,
        })
        self.assertGreaterEqual(report.check_count, 10)

    def test_alert_count(self):
        report = self.env['haccp.report'].create({
            'date_start': self.date_start,
            'date_end': self.date_end,
        })
        self.assertGreaterEqual(report.alert_count, 1)

    def test_state_default_draft(self):
        report = self.env['haccp.report'].create({
            'date_start': self.date_start,
            'date_end': self.date_end,
        })
        self.assertEqual(report.state, 'draft')

    def test_responsible_default_current_user(self):
        report = self.env['haccp.report'].create({
            'date_start': self.date_start,
            'date_end': self.date_end,
        })
        self.assertEqual(report.responsible_id, self.env.user)
```

- [ ] **Step 2 : Déployer et vérifier que les tests échouent**

```bash
./scripts/deploy-haccp-report.sh --test 2>&1 | grep -E 'ERROR|FAIL|OK|test_'
```

Attendu : erreur "ModuleNotFoundError" ou "no module named haccp_report" car le modèle n'existe pas encore.

- [ ] **Step 3 : Écrire `haccp_report.py`**

```python
# odoo-addons/haccp_report/models/haccp_report.py
from odoo import api, fields, models
from odoo.tools.translate import _


class HaccpReport(models.Model):
    _name = 'haccp.report'
    _description = 'Rapport HACCP DDPP'
    _order = 'date_start desc'

    name = fields.Char(
        string='Référence',
        compute='_compute_name',
        store=True,
    )
    date_start = fields.Date(string='Date de début', required=True)
    date_end = fields.Date(string='Date de fin', required=True)
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsable qualité',
        required=True,
        default=lambda self: self.env.user,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        [('draft', 'Brouillon'), ('generated', 'Généré')],
        string='État',
        default='draft',
        required=True,
    )
    check_count = fields.Integer(
        string='Nb mesures',
        compute='_compute_counts',
    )
    alert_count = fields.Integer(
        string='Nb alertes',
        compute='_compute_counts',
    )

    @api.depends('date_start', 'date_end')
    def _compute_name(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                start = rec.date_start.strftime('%d/%m/%Y')
                end = rec.date_end.strftime('%d/%m/%Y')
                rec.name = f'Rapport HACCP DDPP – {start} → {end}'
            else:
                rec.name = _('Nouveau rapport HACCP')

    def _get_date_domain_dt(self):
        """Return (date_start_dt, date_end_dt) as datetimes for domain filters."""
        self.ensure_one()
        date_start_dt = fields.Datetime.to_datetime(self.date_start)
        date_end_dt = fields.Datetime.to_datetime(self.date_end).replace(
            hour=23, minute=59, second=59
        )
        return date_start_dt, date_end_dt

    def _compute_counts(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                start_dt, end_dt = rec._get_date_domain_dt()
                rec.check_count = self.env['quality.check'].search_count([
                    ('create_date', '>=', start_dt),
                    ('create_date', '<=', end_dt),
                ])
                rec.alert_count = self.env['quality.alert'].search_count([
                    ('create_date', '>=', start_dt),
                    ('create_date', '<=', end_dt),
                ])
            else:
                rec.check_count = 0
                rec.alert_count = 0

    def action_print_report(self):
        self.ensure_one()
        result = self.env.ref('haccp_report.action_report_haccp_ddpp').report_action(self)
        self.write({'state': 'generated'})
        return result

    def action_view_checks(self):
        self.ensure_one()
        start_dt, end_dt = self._get_date_domain_dt()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contrôles qualité',
            'res_model': 'quality.check',
            'view_mode': 'list,form',
            'domain': [
                ('create_date', '>=', start_dt),
                ('create_date', '<=', end_dt),
            ],
        }

    def action_view_alerts(self):
        self.ensure_one()
        start_dt, end_dt = self._get_date_domain_dt()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Alertes qualité',
            'res_model': 'quality.alert',
            'view_mode': 'list,form',
            'domain': [
                ('create_date', '>=', start_dt),
                ('create_date', '<=', end_dt),
            ],
        }
```

- [ ] **Step 4 : Créer le fichier security minimal pour que le module s'installe**

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_haccp_report_user,haccp.report user,model_haccp_report,quality.group_quality_user,1,1,1,0
access_haccp_report_manager,haccp.report manager,model_haccp_report,quality.group_quality_manager,1,1,1,1
```

Sauvegarder dans `odoo-addons/haccp_report/security/ir.model.access.csv`.

- [ ] **Step 5 : Créer les fichiers XML vides pour que le manifest soit valide**

Ces fichiers doivent exister (même vides) pour que le module s'installe sans erreur :

```xml
<!-- odoo-addons/haccp_report/report/report_action.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<odoo><data/></odoo>
```

```xml
<!-- odoo-addons/haccp_report/report/report_template.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<odoo><data/></odoo>
```

```xml
<!-- odoo-addons/haccp_report/views/haccp_report_views.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<odoo><data/></odoo>
```

```xml
<!-- odoo-addons/haccp_report/views/menu.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<odoo><data/></odoo>
```

```xml
<!-- odoo-addons/haccp_report/views/quality_inherit.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<odoo><data/></odoo>
```

- [ ] **Step 6 : Déployer + installer le module pour la première fois**

```bash
./scripts/deploy-haccp-report.sh --install 2>&1 | tail -20
```

Attendu : `...Module haccp_report loaded...` sans erreur Python.

- [ ] **Step 7 : Lancer les tests — vérifier qu'ils passent**

```bash
./scripts/deploy-haccp-report.sh --test 2>&1 | grep -E 'ERROR|FAIL|Ran|OK'
```

Attendu :
```
Ran 5 tests in X.XXXs
OK
```

- [ ] **Step 8 : Commit**

```bash
git add odoo-addons/haccp_report/
git commit -m "feat(haccp_report): modèle persistant haccp.report + tests"
```

---

## Task 3 : AbstractModel renderer `_get_report_values()`

**Files:**
- Create: `odoo-addons/haccp_report/models/report_renderer.py`
- Modify: `odoo-addons/haccp_report/tests/test_haccp_report.py` (ajouter tests renderer)

- [ ] **Step 1 : Ajouter les tests du renderer dans `test_haccp_report.py`**

Ajouter cette classe à la fin du fichier de tests existant :

```python
class TestHaccpReportRenderer(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.point = cls.env['quality.point'].create({
            'name': 'TEST-Frigo-Renderer',
            'tolerance_min': -30.0,
            'tolerance_max': 4.0,
            'norm_unit': '°C',
        })
        cls.today = date.today()
        cls.date_start = cls.today - timedelta(days=1)
        cls.date_end = cls.today

        for _ in range(9):
            cls.env['quality.check'].create({
                'point_id': cls.point.id,
                'measure': 2.5,
                'quality_state': 'pass',
            })
        cls.fail_check = cls.env['quality.check'].create({
            'point_id': cls.point.id,
            'measure': 5.8,
            'quality_state': 'fail',
        })
        cls.env['quality.alert'].create({
            'title': 'Alerte renderer test',
            'check_id': cls.fail_check.id,
        })
        cls.report = cls.env['haccp.report'].create({
            'date_start': cls.date_start,
            'date_end': cls.date_end,
        })

    def _get_values(self):
        renderer = self.env['report.haccp_report.report_haccp_ddpp']
        return renderer._get_report_values([self.report.id])

    def test_renderer_returns_required_keys(self):
        values = self._get_values()
        for key in ('docs', 'points', 'checks_by_point', 'stats', 'alerts',
                    'company', 'total_checks', 'total_alerts', 'global_rate'):
            self.assertIn(key, values, f"Clé manquante : {key}")

    def test_stats_contains_point(self):
        values = self._get_values()
        point_ids_in_stats = [s['point'].id for s in values['stats']]
        self.assertIn(self.point.id, point_ids_in_stats)

    def test_stats_rate_calculation(self):
        values = self._get_values()
        stat = next(s for s in values['stats'] if s['point'].id == self.point.id)
        # 9 pass sur 10 = 90%
        self.assertEqual(stat['pass_count'], 9)
        self.assertEqual(stat['count'], 10)
        self.assertAlmostEqual(stat['rate'], 90.0, places=0)

    def test_global_rate(self):
        values = self._get_values()
        self.assertGreater(values['global_rate'], 0.0)
        self.assertLessEqual(values['global_rate'], 100.0)

    def test_checks_by_point_keyed_by_point_id(self):
        values = self._get_values()
        self.assertIn(self.point.id, values['checks_by_point'])
        self.assertEqual(len(values['checks_by_point'][self.point.id]), 10)
```

- [ ] **Step 2 : Déployer et vérifier que les tests échouent**

```bash
./scripts/deploy-haccp-report.sh --test 2>&1 | grep -E 'ERROR|FAIL|error'
```

Attendu : erreur `model 'report.haccp_report.report_haccp_ddpp' does not exist`.

- [ ] **Step 3 : Écrire `report_renderer.py`**

```python
# odoo-addons/haccp_report/models/report_renderer.py
from statistics import median
from odoo import api, fields, models


class ReportHaccpDdpp(models.AbstractModel):
    _name = 'report.haccp_report.report_haccp_ddpp'
    _description = 'Renderer Rapport HACCP DDPP'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['haccp.report'].browse(docids)
        report = docs[0]
        start_dt, end_dt = report._get_date_domain_dt()

        all_checks = self.env['quality.check'].search([
            ('create_date', '>=', start_dt),
            ('create_date', '<=', end_dt),
            ('point_id', '!=', False),
        ], order='create_date asc')

        point_ids = all_checks.mapped('point_id')

        checks_by_point = {
            pt.id: all_checks.filtered(lambda c, p=pt: c.point_id.id == p.id)
            for pt in point_ids
        }

        stats = []
        for point in point_ids:
            point_checks = checks_by_point[point.id]
            count = len(point_checks)
            if count == 0:
                continue
            pass_count = len(point_checks.filtered(lambda c: c.quality_state == 'pass'))
            rate = round(pass_count / count * 100, 1) if count else 0.0
            measures = [c.measure for c in point_checks]
            val_min = round(min(measures), 1) if measures else 0.0
            val_max = round(max(measures), 1) if measures else 0.0
            val_avg = round(sum(measures) / len(measures), 1) if measures else 0.0
            alert_count = self.env['quality.alert'].search_count([
                ('check_id', 'in', point_checks.ids),
            ])
            stats.append({
                'point': point,
                'count': count,
                'pass_count': pass_count,
                'rate': rate,
                'val_min': val_min,
                'val_max': val_max,
                'val_avg': val_avg,
                'alert_count': alert_count,
                'frequency': self._compute_frequency(point_checks),
            })

        alerts = self.env['quality.alert'].search([
            ('create_date', '>=', start_dt),
            ('create_date', '<=', end_dt),
        ], order='create_date asc')

        total_checks = sum(s['count'] for s in stats)
        total_pass = sum(s['pass_count'] for s in stats)
        global_rate = round(total_pass / total_checks * 100, 1) if total_checks else 0.0

        return {
            'docs': docs,
            'points': point_ids,
            'checks_by_point': checks_by_point,
            'stats': stats,
            'alerts': alerts,
            'company': report.company_id,
            'total_checks': total_checks,
            'total_alerts': len(alerts),
            'global_rate': global_rate,
        }

    def _compute_frequency(self, checks):
        if len(checks) < 2:
            return '10 min (continu)'
        dates = sorted(c.create_date for c in checks)
        intervals = [
            (dates[i] - dates[i - 1]).total_seconds() / 60
            for i in range(1, len(dates))
        ]
        med = median(intervals)
        if med < 15:
            return '10 min (continu)'
        if med < 70:
            return f'{int(round(med))} min'
        return f'{round(med / 60, 1)} h'
```

- [ ] **Step 4 : Déployer + mettre à jour + lancer les tests**

```bash
./scripts/deploy-haccp-report.sh --update && ./scripts/deploy-haccp-report.sh --test 2>&1 | grep -E 'Ran|OK|FAIL|ERROR'
```

Attendu : `Ran N tests in X.XXXs` / `OK`

- [ ] **Step 5 : Commit**

```bash
git add odoo-addons/haccp_report/models/report_renderer.py \
        odoo-addons/haccp_report/tests/test_haccp_report.py
git commit -m "feat(haccp_report): AbstractModel renderer + _get_report_values() + tests"
```

---

## Task 4 : Action rapport + Template QWeb (6 sections)

**Files:**
- Modify: `odoo-addons/haccp_report/report/report_action.xml`
- Modify: `odoo-addons/haccp_report/report/report_template.xml`

- [ ] **Step 1 : Écrire `report_action.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data>
    <report
      id="action_report_haccp_ddpp"
      name="Rapport HACCP DDPP"
      model="haccp.report"
      report_type="qweb-pdf"
      print_report_name="'Rapport-HACCP-DDPP-' + object.date_start.strftime('%Y%m%d') + '-' + object.date_end.strftime('%Y%m%d')"
      file="haccp_report.report_haccp_ddpp"
      string="Générer le PDF HACCP DDPP"
      attachment_use="True"
      attachment="'Rapport-HACCP-DDPP-' + object.date_start.strftime('%Y%m%d') + '-' + object.date_end.strftime('%Y%m%d') + '.pdf'"
      paperformat="paperformat_euro"
    />
  </data>
</odoo>
```

- [ ] **Step 2 : Écrire `report_template.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <template id="report_haccp_ddpp">
    <t t-call="web.html_container">
      <t t-foreach="docs" t-as="o">
        <t t-call="web.external_layout">

          <div class="page" style="font-family: Arial, sans-serif; font-size: 11px; color: #111;">

            <style>
              .haccp-section-title {
                font-size: 10px; font-weight: bold; color: #1a5276;
                text-transform: uppercase; letter-spacing: 0.5px;
                border-left: 3px solid #1a5276; padding-left: 6px;
                margin: 16px 0 8px 0;
              }
              .haccp-section-title.alert { border-left-color: #c0392b; color: #c0392b; }
              .haccp-table { width: 100%; border-collapse: collapse; font-size: 9.5px; margin-bottom: 8px; }
              .haccp-table th {
                background-color: #1a5276; color: #fff;
                padding: 4px 6px; text-align: left;
              }
              .haccp-table td { padding: 3px 6px; border-bottom: 1px solid #e8e8e8; }
              .haccp-table tr:nth-child(even) td { background-color: #f7f9fc; }
              .haccp-table tr.fail td { background-color: #fdf0f0; }
              .pass { color: #1a7a1a; font-weight: bold; }
              .fail { color: #c0392b; font-weight: bold; }
              .rate-green { color: #27ae60; font-weight: bold; }
              .rate-orange { color: #e67e22; font-weight: bold; }
              .rate-red { color: #c0392b; font-weight: bold; }
              .total-row td { background-color: #e8f0fe !important; font-weight: bold; }
              .section-break { page-break-before: always; }
              .legal-note { font-size: 8px; color: #888; font-style: italic; margin-top: 6px; }
            </style>

            <!-- ═══════════════════════════════════════════════════
                 EN-TÊTE RAPPORT (période + responsable)
                 ═══════════════════════════════════════════════════ -->
            <table style="width:100%; margin-bottom:16px;">
              <tr>
                <td style="vertical-align:top;">
                  <div style="font-size:8px; color:#888; text-transform:uppercase; letter-spacing:1px;">
                    Rapport de surveillance HACCP
                  </div>
                  <div style="font-size:7px; color:#555; margin-top:2px;">
                    Responsable qualité : <t t-esc="o.responsible_id.name"/>
                  </div>
                </td>
                <td style="text-align:right; vertical-align:top;">
                  <div style="display:inline-block; background:#1a5276; color:#fff; padding:4px 12px; border-radius:4px; font-weight:bold; font-size:9px;">
                    <t t-esc="o.date_start.strftime('%d/%m/%Y')"/> – <t t-esc="o.date_end.strftime('%d/%m/%Y')"/>
                  </div>
                  <div style="font-size:8px; color:#888; margin-top:3px;">
                    Édité le <t t-esc="context_timestamp(datetime.datetime.now()).strftime('%d/%m/%Y à %H:%M')"/>
                  </div>
                </td>
              </tr>
            </table>

            <!-- ═══════════════════════════════════════════════════
                 SECTION 0 — PLAN HACCP (CCP)
                 ═══════════════════════════════════════════════════ -->
            <div class="haccp-section-title">Plan HACCP — Points Critiques de Contrôle</div>
            <table class="haccp-table">
              <thead>
                <tr>
                  <th>Équipement / Zone</th>
                  <th>Paramètre</th>
                  <th style="text-align:center;">Limite critique</th>
                  <th style="text-align:center;">Fréquence</th>
                  <th>Action corrective prévue</th>
                </tr>
              </thead>
              <tbody>
                <t t-foreach="stats" t-as="stat">
                  <tr>
                    <td><t t-esc="stat['point'].display_name"/></td>
                    <td>
                      <t t-if="stat['point'].norm_unit and '°' in stat['point'].norm_unit">Température</t>
                      <t t-elif="stat['point'].norm_unit and '%' in stat['point'].norm_unit">Humidité relative</t>
                      <t t-else="">Mesure (<t t-esc="stat['point'].norm_unit"/>)</t>
                    </td>
                    <td style="text-align:center; font-weight:bold;">
                      ≤ <t t-esc="stat['point'].tolerance_max"/> <t t-esc="stat['point'].norm_unit"/>
                    </td>
                    <td style="text-align:center;"><t t-esc="stat['frequency']"/></td>
                    <td style="font-size:8.5px;">
                      <t t-if="stat['point'].failure_message">
                        <t t-out="stat['point'].failure_message"/>
                      </t>
                      <t t-else="">Vérification + action corrective immédiate</t>
                    </td>
                  </tr>
                </t>
              </tbody>
            </table>
            <div class="legal-note">
              Surveillance automatique 24h/24 par capteurs LoRaWAN — Seuils conformes à l'Arrêté du 21/12/2009
              et au Règlement CE 852/2004 (Article 5).
            </div>

            <!-- ═══════════════════════════════════════════════════
                 SECTION 2 — TABLEAU DE SYNTHÈSE
                 ═══════════════════════════════════════════════════ -->
            <div class="haccp-section-title" style="margin-top:18px;">Synthèse de la période</div>
            <table class="haccp-table">
              <thead>
                <tr>
                  <th>Équipement</th>
                  <th style="text-align:center;">Nb mesures</th>
                  <th style="text-align:center;">Seuil</th>
                  <th style="text-align:center;">Min</th>
                  <th style="text-align:center;">Max</th>
                  <th style="text-align:center;">Moyenne</th>
                  <th style="text-align:center;">Conformité</th>
                  <th style="text-align:center;">Alertes</th>
                </tr>
              </thead>
              <tbody>
                <t t-foreach="stats" t-as="stat">
                  <tr>
                    <td><t t-esc="stat['point'].display_name"/></td>
                    <td style="text-align:center;"><t t-esc="stat['count']"/></td>
                    <td style="text-align:center;">
                      ≤ <t t-esc="stat['point'].tolerance_max"/> <t t-esc="stat['point'].norm_unit"/>
                    </td>
                    <td style="text-align:center;"><t t-esc="stat['val_min']"/> <t t-esc="stat['point'].norm_unit"/></td>
                    <td style="text-align:center;"><t t-esc="stat['val_max']"/> <t t-esc="stat['point'].norm_unit"/></td>
                    <td style="text-align:center;"><t t-esc="stat['val_avg']"/> <t t-esc="stat['point'].norm_unit"/></td>
                    <td style="text-align:center;"
                        t-att-class="'rate-green' if stat['rate'] >= 99 else ('rate-orange' if stat['rate'] >= 95 else 'rate-red')">
                      <t t-esc="stat['rate']"/>%
                    </td>
                    <td style="text-align:center;"
                        t-att-class="'fail' if stat['alert_count'] > 0 else ''">
                      <t t-esc="stat['alert_count']"/>
                    </td>
                  </tr>
                </t>
                <tr class="total-row">
                  <td>TOTAL</td>
                  <td style="text-align:center;"><t t-esc="total_checks"/></td>
                  <td></td><td></td><td></td><td></td>
                  <td style="text-align:center;"
                      t-att-class="'rate-green' if global_rate >= 99 else ('rate-orange' if global_rate >= 95 else 'rate-red')">
                    <t t-esc="global_rate"/>%
                  </td>
                  <td style="text-align:center;"
                      t-att-class="'fail' if total_alerts > 0 else ''">
                    <t t-esc="total_alerts"/>
                  </td>
                </tr>
              </tbody>
            </table>

            <!-- ═══════════════════════════════════════════════════
                 SECTION 3 — RELEVÉS DÉTAILLÉS (par CCP)
                 ═══════════════════════════════════════════════════ -->
            <t t-foreach="stats" t-as="stat">
              <t t-set="point_checks" t-value="checks_by_point.get(stat['point'].id)"/>
              <div class="section-break"/>
              <div class="haccp-section-title">
                Relevés détaillés — <t t-esc="stat['point'].display_name"/>
              </div>
              <table class="haccp-table">
                <thead>
                  <tr>
                    <th>Date / Heure</th>
                    <th style="text-align:center;">Valeur mesurée</th>
                    <th style="text-align:center;">Seuil</th>
                    <th style="text-align:center;">Statut</th>
                  </tr>
                </thead>
                <tbody>
                  <t t-foreach="point_checks" t-as="chk">
                    <tr t-att-class="'fail' if chk.quality_state == 'fail' else ''">
                      <td><t t-esc="chk.create_date.strftime('%d/%m/%Y %H:%M')"/></td>
                      <td style="text-align:center;"
                          t-att-class="'fail' if chk.quality_state == 'fail' else ''">
                        <t t-esc="round(chk.measure, 1)"/> <t t-esc="chk.norm_unit"/>
                      </td>
                      <td style="text-align:center;">
                        ≤ <t t-esc="chk.tolerance_max"/> <t t-esc="chk.norm_unit"/>
                      </td>
                      <td style="text-align:center;"
                          t-att-class="'pass' if chk.quality_state == 'pass' else 'fail'">
                        <t t-if="chk.quality_state == 'pass'">✓</t>
                        <t t-else="">✗</t>
                      </td>
                    </tr>
                  </t>
                </tbody>
              </table>
            </t>

            <!-- ═══════════════════════════════════════════════════
                 SECTION 4 — NON-CONFORMITÉS
                 ═══════════════════════════════════════════════════ -->
            <div class="section-break"/>
            <div class="haccp-section-title alert">Non-conformités et actions correctives</div>
            <t t-if="not alerts">
              <div style="padding:10px; background:#f0f9f0; border:1px solid #c8e6c9; border-radius:4px; font-size:10px; color:#1a7a1a;">
                ✓ Aucune non-conformité enregistrée sur la période.
              </div>
            </t>
            <t t-if="alerts">
              <t t-foreach="alerts" t-as="alert">
                <div style="border:1px solid #f5b7b1; border-radius:4px; padding:8px 12px; margin-bottom:8px; background:#fdf8f8;">
                  <table style="width:100%; font-size:9px; border-collapse:collapse;">
                    <tr>
                      <td style="width:50%; vertical-align:top;">
                        <strong><t t-esc="alert.display_name"/></strong>
                        — <t t-esc="alert.check_id.point_id.display_name if alert.check_id else 'N/A'"/>
                      </td>
                      <td style="text-align:right; vertical-align:top;">
                        <span t-att-style="'background:#c0392b;color:#fff;padding:2px 8px;border-radius:3px;' if not alert.stage_id.done else 'background:#27ae60;color:#fff;padding:2px 8px;border-radius:3px;'">
                          <t t-if="alert.stage_id.done">Clôturée</t>
                          <t t-else="">Ouverte</t>
                        </span>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding-top:4px; color:#555;">
                        Valeur : <strong class="fail">
                          <t t-esc="round(alert.check_id.measure, 1) if alert.check_id else 'N/A'"/>
                          <t t-esc="alert.check_id.norm_unit if alert.check_id else ''"/>
                        </strong>
                        — Seuil : ≤ <t t-esc="alert.check_id.tolerance_max if alert.check_id else 'N/A'"/>
                        <t t-esc="alert.check_id.norm_unit if alert.check_id else ''"/>
                      </td>
                      <td style="text-align:right; color:#555; padding-top:4px;">
                        Ouverte le : <t t-esc="alert.date_assign.strftime('%d/%m/%Y') if alert.date_assign else 'N/A'"/>
                        <t t-if="alert.date_close">
                          — Clôturée le : <t t-esc="alert.date_close.strftime('%d/%m/%Y')"/>
                        </t>
                      </td>
                    </tr>
                    <t t-if="alert.action_corrective">
                      <tr>
                        <td colspan="2" style="padding-top:4px; color:#333;">
                          <strong>Action corrective :</strong>
                          <t t-out="alert.action_corrective"/>
                        </td>
                      </tr>
                    </t>
                    <tr>
                      <td colspan="2" style="padding-top:3px; color:#888; font-size:8.5px;">
                        Responsable : <t t-esc="alert.user_id.name if alert.user_id else 'Non assigné'"/>
                      </td>
                    </tr>
                  </table>
                </div>
              </t>
            </t>

            <!-- ═══════════════════════════════════════════════════
                 SECTION 5 — SIGNATURE
                 ═══════════════════════════════════════════════════ -->
            <div style="margin-top:30px; border-top:1px solid #ddd; padding-top:14px;">
              <table style="width:100%; font-size:9px;">
                <tr>
                  <td style="vertical-align:bottom; color:#888;">
                    <div>Archivage obligatoire 3 ans — Art. 5 Règlement CE 852/2004</div>
                    <div>Généré par Odoo 19 — AIFluence Digital</div>
                  </td>
                  <td style="text-align:center; vertical-align:bottom;">
                    <div style="border:1px solid #ccc; width:160px; height:50px; margin:0 auto; display:inline-block;"/>
                    <div style="margin-top:4px;">
                      <t t-esc="o.responsible_id.name"/> — <t t-esc="o.date_end.strftime('%d/%m/%Y')"/>
                    </div>
                  </td>
                </tr>
              </table>
            </div>

          </div>
        </t>
      </t>
    </t>
  </template>
</odoo>
```

- [ ] **Step 3 : Déployer + mettre à jour**

```bash
./scripts/deploy-haccp-report.sh --update 2>&1 | tail -10
```

Attendu : pas d'erreur XML/QWeb.

- [ ] **Step 4 : Test de rendu HTML du rapport (debug)**

Dans le navigateur, activer le mode développeur (`?debug=1`), puis ouvrir :
```
http://192.168.1.182:8029/report/html/haccp_report.action_report_haccp_ddpp/<ID_RECORD>
```

Vérifier que les 6 sections s'affichent correctement. Corriger le CSS si nécessaire.

- [ ] **Step 5 : Commit**

```bash
git add odoo-addons/haccp_report/report/
git commit -m "feat(haccp_report): QWeb template 6 sections + ir.actions.report"
```

---

## Task 5 : Vues Odoo — Form view + List view

**Files:**
- Modify: `odoo-addons/haccp_report/views/haccp_report_views.xml`

- [ ] **Step 1 : Écrire `haccp_report_views.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data>

    <!-- ══════════════════ FORM VIEW ══════════════════ -->
    <record id="haccp_report_form_view" model="ir.ui.view">
      <field name="name">haccp.report.form</field>
      <field name="model">haccp.report</field>
      <field name="arch" type="xml">
        <form string="Rapport HACCP DDPP">
          <header>
            <button name="action_print_report"
                    string="🖨️ Générer le PDF"
                    type="object"
                    class="oe_highlight"/>
            <field name="state" widget="statusbar"
                   statusbar_visible="draft,generated"/>
          </header>

          <sheet>
            <div name="button_box" class="oe_button_box">
              <button name="action_view_checks"
                      type="object"
                      class="oe_stat_button"
                      icon="fa-thermometer-half">
                <field name="check_count" widget="statinfo" string="Mesures"/>
              </button>
              <button name="action_view_alerts"
                      type="object"
                      class="oe_stat_button"
                      icon="fa-exclamation-triangle"
                      invisible="alert_count == 0">
                <field name="alert_count" widget="statinfo" string="Alertes"/>
              </button>
            </div>

            <div class="oe_title">
              <h1><field name="name" readonly="1"/></h1>
            </div>

            <group>
              <group string="Période de surveillance">
                <field name="date_start"/>
                <field name="date_end"/>
              </group>
              <group string="Responsable">
                <field name="responsible_id"/>
                <field name="company_id" groups="base.group_multi_company"/>
              </group>
            </group>
          </sheet>

          <div class="oe_chatter">
            <field name="message_follower_ids"/>
            <field name="message_ids"/>
          </div>
        </form>
      </field>
    </record>

    <!-- ══════════════════ LIST VIEW ══════════════════ -->
    <record id="haccp_report_list_view" model="ir.ui.view">
      <field name="name">haccp.report.list</field>
      <field name="model">haccp.report</field>
      <field name="arch" type="xml">
        <list string="Rapports HACCP DDPP" default_order="date_start desc">
          <field name="name"/>
          <field name="date_start"/>
          <field name="date_end"/>
          <field name="responsible_id"/>
          <field name="check_count" string="Mesures"/>
          <field name="alert_count" string="Alertes"
                 decoration-danger="alert_count > 0"/>
          <field name="state" widget="badge"
                 decoration-success="state == 'generated'"
                 decoration-muted="state == 'draft'"/>
        </list>
      </field>
    </record>

    <!-- ══════════════════ ACTION WINDOW ══════════════════ -->
    <record id="haccp_report_action" model="ir.actions.act_window">
      <field name="name">Rapports HACCP DDPP</field>
      <field name="res_model">haccp.report</field>
      <field name="view_mode">list,form</field>
      <field name="help" type="html">
        <p class="o_view_nocontent_smiling_face">
          Créer votre premier rapport HACCP DDPP
        </p>
        <p>
          Sélectionnez une période pour générer un rapport PDF réglementaire
          incluant tous les relevés de température et les non-conformités.
        </p>
      </field>
    </record>

  </data>
</odoo>
```

- [ ] **Step 2 : Activer le chatter sur le modèle**

Ajouter `_inherit = ['mail.thread']` dans `haccp_report.py` et `'mail'` dans les dépendances du manifest :

Dans `haccp_report.py`, modifier la définition de classe :
```python
class HaccpReport(models.Model):
    _name = 'haccp.report'
    _description = 'Rapport HACCP DDPP'
    _order = 'date_start desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
```

Dans `__manifest__.py`, modifier `depends` :
```python
'depends': ['quality_control', 'web', 'mail'],
```

- [ ] **Step 3 : Déployer + mettre à jour**

```bash
./scripts/deploy-haccp-report.sh --update 2>&1 | tail -10
```

- [ ] **Step 4 : Vérifier dans le navigateur**

Ouvrir `http://192.168.1.182:8029/web#action=haccp_report.haccp_report_action` et vérifier que la list view et la form view s'affichent correctement.

- [ ] **Step 5 : Commit**

```bash
git add odoo-addons/haccp_report/views/haccp_report_views.xml \
        odoo-addons/haccp_report/models/haccp_report.py \
        odoo-addons/haccp_report/__manifest__.py
git commit -m "feat(haccp_report): form view + list view + chatter"
```

---

## Task 6 : Menu Qualité > Rapports + bouton smart dans quality.check

**Files:**
- Modify: `odoo-addons/haccp_report/views/menu.xml`
- Modify: `odoo-addons/haccp_report/views/quality_inherit.xml`

- [ ] **Step 1 : Écrire `menu.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data>
    <!-- Sous-menu Rapports dans l'app Qualité -->
    <menuitem
      id="menu_haccp_reports_root"
      name="Rapports"
      parent="quality.menu_quality_root"
      sequence="20"/>

    <menuitem
      id="menu_haccp_report_ddpp"
      name="Rapports HACCP DDPP"
      parent="menu_haccp_reports_root"
      action="haccp_report_action"
      sequence="10"/>
  </data>
</odoo>
```

> **Note :** Vérifier que `quality.menu_quality_root` est le bon xml_id du menu parent.
> Si erreur "External ID not found", inspecter avec :
> ```bash
> ssh christian@192.168.1.182 "docker exec odoo19e_app odoo shell -d odoo19e_dev --no-http -c \"print(env.ref('quality.menu_quality_root').name)\""
> ```

- [ ] **Step 2 : Écrire `quality_inherit.xml`**

Ajouter un bouton "Rapport HACCP DDPP" dans le control panel de la list view quality.check.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data>
    <record id="quality_check_list_inherit_haccp" model="ir.ui.view">
      <field name="name">quality.check.list.haccp.inherit</field>
      <field name="model">quality.check</field>
      <field name="inherit_id" ref="quality_control.quality_check_list_view"/>
      <field name="arch" type="xml">
        <xpath expr="//list" position="attributes">
          <attribute name="class">o_list_view</attribute>
        </xpath>
      </field>
    </record>

    <!-- Bouton dans la barre d'actions de la vue quality.check -->
    <record id="quality_check_action_haccp_report" model="ir.actions.server">
      <field name="name">📊 Rapport HACCP DDPP</field>
      <field name="model_id" ref="quality_control.model_quality_check"/>
      <field name="binding_model_id" ref="quality_control.model_quality_check"/>
      <field name="binding_view_types">list</field>
      <field name="state">code</field>
      <field name="code">
import datetime
today = datetime.date.today()
first_day = today.replace(day=1)
action = {
    'type': 'ir.actions.act_window',
    'name': 'Nouveau Rapport HACCP DDPP',
    'res_model': 'haccp.report',
    'view_mode': 'form',
    'target': 'current',
    'context': {
        'default_date_start': first_day.isoformat(),
        'default_date_end': today.isoformat(),
        'default_responsible_id': env.user.id,
    },
}
      </field>
    </record>
  </data>
</odoo>
```

> **Note :** Vérifier que `quality_control.quality_check_list_view` est le bon xml_id.
> Si erreur, inspecter avec :
> ```bash
> ssh christian@192.168.1.182 "docker exec -it odoo19e_app odoo shell -d odoo19e_dev --no-http -c \"views = env['ir.ui.view'].search([('model','=','quality.check'),('type','=','list')]); [print(v.xml_id, v.name) for v in views]\""
> ```

- [ ] **Step 3 : Déployer + mettre à jour**

```bash
./scripts/deploy-haccp-report.sh --update 2>&1 | tail -15
```

- [ ] **Step 4 : Vérifier le menu dans le navigateur**

Ouvrir `http://192.168.1.182:8029` et naviguer vers Qualité > Rapports > Rapports HACCP DDPP.

Vérifier que le bouton "📊 Rapport HACCP DDPP" apparaît dans Qualité > Contrôles.

- [ ] **Step 5 : Corriger le xml_id du menu parent si besoin**

Si le menu "Rapports" n'apparaît pas sous "Qualité", chercher le bon parent :
```bash
ssh christian@192.168.1.182 "docker exec odoo19e_app odoo shell -d odoo19e_dev --no-http -c \"
menus = env['ir.ui.menu'].search([('name', 'ilike', 'qualit')])
for m in menus: print(m.complete_name, '->', m.xml_id)
\""
```

- [ ] **Step 6 : Commit**

```bash
git add odoo-addons/haccp_report/views/menu.xml \
        odoo-addons/haccp_report/views/quality_inherit.xml
git commit -m "feat(haccp_report): menu Qualité > Rapports + bouton quality.check"
```

---

## Task 7 : Test de bout en bout

- [ ] **Step 1 : Lancer tous les tests du module**

```bash
./scripts/deploy-haccp-report.sh --test 2>&1 | grep -E 'Ran|OK|FAIL|ERROR|test_'
```

Attendu : toutes les classes `TestHaccpReport` et `TestHaccpReportRenderer` passent.

- [ ] **Step 2 : Test manuel dans le navigateur — génération du PDF**

1. Ouvrir `http://192.168.1.182:8029` (login admin)
2. Aller dans Qualité > Rapports > Rapports HACCP DDPP
3. Cliquer "Nouveau"
4. Renseigner date_début = 01/05/2026, date_fin = 21/05/2026
5. Vérifier que `check_count` et `alert_count` s'affichent dans les stat buttons
6. Cliquer "🖨️ Générer le PDF"
7. Vérifier que le PDF se télécharge
8. Ouvrir le PDF — vérifier les 6 sections :
   - Section 0 : tableau CCP avec Frigo/Congélateur/Stockage sec
   - Section 1 : en-tête avec nom société + période
   - Section 2 : synthèse avec taux conformité colorisé
   - Section 3 : relevés détaillés par CCP (lignes rouges sur dépassements)
   - Section 4 : non-conformités (ou "Aucune non-conformité")
   - Section 5 : zone de signature + mention légale
9. Vérifier que le record passe en état "Généré"
10. Vérifier que le PDF est attaché dans le chatter

- [ ] **Step 3 : Test du bouton quality.check**

1. Aller dans Qualité > Contrôles
2. Vérifier la présence du bouton "📊 Rapport HACCP DDPP" (dans Actions ou control panel)
3. Cliquer — vérifier que le formulaire haccp.report s'ouvre pré-rempli avec le 1er jour du mois courant

- [ ] **Step 4 : Commit final**

```bash
git add -A
git commit -m "feat(haccp_report): module complet — rapport PDF HACCP DDPP fonctionnel"
```

---

## Task 8 (optionnel) : Affinage layout via Studio EE

Cette tâche n'est pas nécessaire au fonctionnement — elle permet d'ajuster le layout PDF visuellement sans redéployer.

- [ ] **Step 1 : Ouvrir Studio**

Dans Odoo EE, activer le mode développeur puis cliquer sur l'icône Studio (crayon) en haut à droite.

- [ ] **Step 2 : Naviguer vers le rapport**

Studio > Reports > chercher "Rapport HACCP DDPP" > cliquer sur les 3 points > Modifier (ou dupliquer si tu veux garder l'original intact).

- [ ] **Step 3 : Utiliser l'éditeur XML Studio**

Studio génère automatiquement une extension QWeb (`inherit`) — les modifications n'écrasent pas `report_template.xml`.
Ajustements typiques : marges, taille de police, couleurs d'en-tête, logo placement.

- [ ] **Step 4 : Exporter la customisation Studio**

Si les modifications Studio doivent être versionnées, exporter le module Studio via :
Paramètres > Technique > Interface utilisateur > Vues > filtrer par module `studio_customization` > exporter.
