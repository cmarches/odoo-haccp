from datetime import timedelta

from odoo import models


class ReportHaccpDdpp(models.AbstractModel):
    _name = 'report.haccp_report.report_haccp_ddpp'
    _description = 'Renderer rapport HACCP DDPP'

    # -------------------------------------------------------------------------
    # Public API (called by Odoo report engine + tests)
    # -------------------------------------------------------------------------

    def _get_report_values(self, docids_or_record, data=None):
        """Return the template context dict for the HACCP DDPP report.

        Parameters
        ----------
        docids_or_record : int | list[int] | haccp.report recordset
            When called by the Odoo report engine the argument is a list of
            record IDs.  When called directly from tests it may be a recordset.
        data : dict | None
            Optional extra data (unused here, kept for Odoo API compatibility).

        Returns
        -------
        dict with keys:
            docs, points, checks_by_point, stats, alerts,
            company, total_checks, total_alerts, global_rate
        """
        # Support both "report engine" call (list of ids) and direct test call
        if hasattr(docids_or_record, '_name'):
            report = docids_or_record
        else:
            ids = [docids_or_record] if isinstance(docids_or_record, int) else list(docids_or_record)
            report = self.env['haccp.report'].browse(ids)

        report.ensure_one()

        start_dt, end_dt = report._get_date_domain_dt()

        # ------------------------------------------------------------------
        # Fetch quality.check records in the date range
        # ------------------------------------------------------------------
        checks = self.env['quality.check'].search([
            ('create_date', '>=', start_dt),
            ('create_date', '<=', end_dt),
        ])

        # ------------------------------------------------------------------
        # Group checks by control point
        # ------------------------------------------------------------------
        checks_by_point = {}  # {point.id (int): recordset}
        for check in checks:
            pid = check.point_id.id
            if pid not in checks_by_point:
                checks_by_point[pid] = self.env['quality.check']
            checks_by_point[pid] |= check

        # Ordered list of distinct control points
        points = self.env['quality.point'].browse(list(checks_by_point.keys()))

        # ------------------------------------------------------------------
        # Fetch alerts in the date range
        # ------------------------------------------------------------------
        alerts = self.env['quality.alert'].search([
            ('create_date', '>=', start_dt),
            ('create_date', '<=', end_dt),
        ])

        # Map alert → check → point for per-point alert counting
        alert_count_by_point = {}
        for alert in alerts:
            if alert.check_id and alert.check_id.point_id:
                pid = alert.check_id.point_id.id
                alert_count_by_point[pid] = alert_count_by_point.get(pid, 0) + 1

        # ------------------------------------------------------------------
        # Build stats list
        # ------------------------------------------------------------------
        period_delta = timedelta(
            seconds=(end_dt - start_dt).total_seconds()
        ) if start_dt and end_dt else timedelta(days=0)

        stats = []
        for point in points:
            point_checks = checks_by_point.get(point.id, self.env['quality.check'])
            count = len(point_checks)
            pass_count = len(point_checks.filtered(lambda c: c.quality_state == 'pass'))
            rate = (pass_count / count * 100.0) if count else 0.0

            measures = [c.measure for c in point_checks if c.measure is not False and c.measure is not None]
            val_min = min(measures) if measures else 0.0
            val_max = max(measures) if measures else 0.0
            val_avg = (sum(measures) / len(measures)) if measures else 0.0

            p_alert_count = alert_count_by_point.get(point.id, 0)
            frequency = self._compute_frequency(point, count, period_delta)

            stats.append({
                'point': point,
                'count': count,
                'pass_count': pass_count,
                'rate': round(rate, 1),
                'val_min': val_min,
                'val_max': val_max,
                'val_avg': round(val_avg, 2),
                'alert_count': p_alert_count,
                'frequency': frequency,
            })

        # ------------------------------------------------------------------
        # Global aggregates
        # ------------------------------------------------------------------
        total_checks = len(checks)
        total_alerts = len(alerts)
        total_pass = sum(1 for c in checks if c.quality_state == 'pass')
        global_rate = round(total_pass / total_checks * 100.0, 1) if total_checks else 0.0

        return {
            'docs': report,
            'points': points,
            'checks_by_point': checks_by_point,
            'stats': stats,
            'alerts': alerts,
            'company': report.company_id,
            'total_checks': total_checks,
            'total_alerts': total_alerts,
            'global_rate': global_rate,
        }

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _compute_frequency(self, point, count, period_delta):
        """Return a human-readable string describing check frequency.

        Parameters
        ----------
        point : quality.point record (unused for now, kept for future rules)
        count : int — number of checks performed in the period
        period_delta : timedelta — duration of the report period

        Returns
        -------
        str — e.g. "~1/jour", "~2/semaine", "N/A"
        """
        if count == 0 or period_delta.total_seconds() == 0:
            return 'N/A'

        days = period_delta.total_seconds() / 86400.0
        if days < 1:
            days = 1.0

        rate_per_day = count / days

        if rate_per_day >= 0.5:
            # At least roughly once every two days → express per-day
            rounded = round(rate_per_day)
            if rounded < 1:
                rounded = 1
            return f'~{rounded}/jour'
        elif rate_per_day >= 1 / 7:
            # At least once a week
            rate_per_week = rate_per_day * 7
            return f'~{round(rate_per_week)}/semaine'
        else:
            rate_per_month = rate_per_day * 30
            if rate_per_month < 1:
                return '<1/mois'
            return f'~{round(rate_per_month)}/mois'
