from datetime import date, datetime, timedelta
from odoo.tests.common import TransactionCase


class TestHaccpReportRenderer(TransactionCase):
    """Tests for the AbstractModel renderer (report.haccp_report.report_haccp_ddpp)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Two control points
        cls.point_frigo = cls.env['quality.point'].create({
            'name': 'TEST-Frigo-R',
            'tolerance_min': -30.0,
            'tolerance_max': 4.0,
            'norm_unit': '°C',
        })
        cls.point_four = cls.env['quality.point'].create({
            'name': 'TEST-Four-R',
            'tolerance_min': 60.0,
            'tolerance_max': 100.0,
            'norm_unit': '°C',
        })
        cls.today = date.today()
        cls.date_start = cls.today - timedelta(days=7)
        cls.date_end = cls.today

        # Frigo: 3 pass, 1 fail
        for _ in range(3):
            cls.env['quality.check'].create({
                'point_id': cls.point_frigo.id,
                'measure': 2.0,
                'quality_state': 'pass',
            })
        cls.failing_check = cls.env['quality.check'].create({
            'point_id': cls.point_frigo.id,
            'measure': 6.0,
            'quality_state': 'fail',
        })
        cls.alert = cls.env['quality.alert'].create({
            'title': 'Alerte frigo R',
            'check_id': cls.failing_check.id,
            'action_corrective': '<p>Vérification joint</p>',
        })

        # Four: 2 pass
        for _ in range(2):
            cls.env['quality.check'].create({
                'point_id': cls.point_four.id,
                'measure': 75.0,
                'quality_state': 'pass',
            })

        cls.report = cls.env['haccp.report'].create({
            'date_start': cls.date_start,
            'date_end': cls.date_end,
        })
        cls.renderer = cls.env['report.haccp_report.report_haccp_ddpp']
        cls.values = cls.renderer._get_report_values(cls.report, data=None)

    # --- Return structure ---

    def test_returns_docs_key(self):
        self.assertIn('docs', self.values)

    def test_docs_is_report_recordset(self):
        self.assertEqual(self.values['docs'], self.report)

    def test_returns_points_key(self):
        self.assertIn('points', self.values)

    def test_returns_checks_by_point_key(self):
        self.assertIn('checks_by_point', self.values)

    def test_returns_stats_key(self):
        self.assertIn('stats', self.values)

    def test_returns_alerts_key(self):
        self.assertIn('alerts', self.values)

    def test_returns_company_key(self):
        self.assertIn('company', self.values)

    def test_returns_total_checks_key(self):
        self.assertIn('total_checks', self.values)

    def test_returns_total_alerts_key(self):
        self.assertIn('total_alerts', self.values)

    def test_returns_global_rate_key(self):
        self.assertIn('global_rate', self.values)

    # --- checks_by_point keyed by integer point.id ---

    def test_checks_by_point_keys_are_integers(self):
        for key in self.values['checks_by_point']:
            self.assertIsInstance(key, int)

    def test_checks_by_point_contains_frigo(self):
        self.assertIn(self.point_frigo.id, self.values['checks_by_point'])

    # --- stats list dicts ---

    def test_stats_is_list(self):
        self.assertIsInstance(self.values['stats'], list)

    def test_stats_dict_keys(self):
        required_keys = {'point', 'count', 'pass_count', 'rate',
                         'val_min', 'val_max', 'val_avg', 'alert_count', 'frequency'}
        for stat in self.values['stats']:
            self.assertTrue(required_keys.issubset(set(stat.keys())),
                            f"Missing keys in stat: {required_keys - set(stat.keys())}")

    def test_stats_frigo_count(self):
        frigo_stat = next(
            s for s in self.values['stats'] if s['point'].id == self.point_frigo.id
        )
        self.assertGreaterEqual(frigo_stat['count'], 4)

    def test_stats_frigo_pass_count(self):
        frigo_stat = next(
            s for s in self.values['stats'] if s['point'].id == self.point_frigo.id
        )
        self.assertGreaterEqual(frigo_stat['pass_count'], 3)

    def test_stats_frigo_rate(self):
        frigo_stat = next(
            s for s in self.values['stats'] if s['point'].id == self.point_frigo.id
        )
        # 3 pass / 4 checks = 75.0
        self.assertAlmostEqual(frigo_stat['rate'], 75.0, places=1)

    def test_stats_frigo_alert_count(self):
        frigo_stat = next(
            s for s in self.values['stats'] if s['point'].id == self.point_frigo.id
        )
        self.assertGreaterEqual(frigo_stat['alert_count'], 1)

    def test_stats_frequency_is_string(self):
        for stat in self.values['stats']:
            self.assertIsInstance(stat['frequency'], str)

    # --- global aggregates ---

    def test_total_checks_positive(self):
        self.assertGreaterEqual(self.values['total_checks'], 6)

    def test_total_alerts_positive(self):
        self.assertGreaterEqual(self.values['total_alerts'], 1)

    def test_global_rate_between_0_and_100(self):
        rate = self.values['global_rate']
        self.assertGreaterEqual(rate, 0.0)
        self.assertLessEqual(rate, 100.0)

    # --- _compute_frequency ---

    def _make_checks_at_intervals(self, point, interval_minutes, count):
        """Create `count` quality.check records spaced `interval_minutes` apart."""
        base = datetime(2026, 1, 1, 8, 0, 0)
        checks = self.env['quality.check']
        for i in range(count):
            c = self.env['quality.check'].create({
                'point_id': point.id,
                'measure': 2.0,
                'quality_state': 'pass',
            })
            # Force create_date via SQL to control spacing
            self.env.cr.execute(
                "UPDATE quality_check SET create_date = %s WHERE id = %s",
                (base + timedelta(minutes=interval_minutes * i), c.id),
            )
            c.invalidate_recordset(['create_date'])
            checks |= c
        return checks

    def test_frequency_continuous_many_close_checks(self):
        """Many checks spaced 10 min → '10 min (continu)'."""
        checks = self._make_checks_at_intervals(self.point_frigo, 10, 12)
        freq = self.renderer._compute_frequency(checks)
        self.assertEqual(freq, '10 min (continu)')

    def test_frequency_continuous_zero_or_one_check(self):
        """0 or 1 check → '10 min (continu)'."""
        empty = self.env['quality.check']
        self.assertEqual(self.renderer._compute_frequency(empty), '10 min (continu)')
        one = self.env['quality.check'].browse(self.failing_check.id)
        self.assertEqual(self.renderer._compute_frequency(one), '10 min (continu)')

    def test_frequency_thirty_minutes(self):
        """Checks spaced ~30 min → '30 min'."""
        checks = self._make_checks_at_intervals(self.point_frigo, 30, 5)
        freq = self.renderer._compute_frequency(checks)
        self.assertEqual(freq, '30 min')

    def test_frequency_two_hours(self):
        """Checks spaced ~2 hours → '2.0 h'."""
        checks = self._make_checks_at_intervals(self.point_frigo, 120, 5)
        freq = self.renderer._compute_frequency(checks)
        self.assertEqual(freq, '2.0 h')


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
            f'Rapport HACCP – {start_str} → {end_str}',
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
