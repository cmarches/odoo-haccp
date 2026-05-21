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
