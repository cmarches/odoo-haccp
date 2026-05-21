from statistics import median

from odoo import models


class ReportHaccpDdpp(models.AbstractModel):
    _name = 'report.haccp_report.report_haccp_ddpp'
    _description = 'Renderer rapport HACCP DDPP'

    # -------------------------------------------------------------------------
    # Public API (called by Odoo report engine + tests)
    # -------------------------------------------------------------------------

    def _get_report_values(self, docids, data=None):
        """Return the template context dict for the HACCP DDPP report.

        Parameters
        ----------
        docids : int | list[int] | haccp.report recordset
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
        if hasattr(docids, '_name'):
            report = docids
        else:
            ids = [docids] if isinstance(docids, int) else list(docids)
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
            if not pid:
                continue
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

        # Map alert → point for per-point alert counting.
        # Primary path: alert.check_id.point_id (standard Odoo quality flow).
        # Fallback: name-based matching for orphan alerts created without check_id
        # (e.g. IoT bridge alerts). We match the point whose display_name contributes
        # the most distinctive words to the alert name.
        alert_count_by_point = {}
        for alert in alerts:
            pid = None
            if alert.check_id and alert.check_id.point_id:
                pid = alert.check_id.point_id.id
            else:
                pid = self._match_alert_to_point(alert, points)
            if pid:
                alert_count_by_point[pid] = alert_count_by_point.get(pid, 0) + 1

        # ------------------------------------------------------------------
        # Build stats list
        # ------------------------------------------------------------------
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
            frequency = self._compute_frequency(point_checks)

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

    def _match_alert_to_point(self, alert, points):
        """Match an orphan alert (no check_id) to the best-fitting quality.point by name.

        Scores each point by counting how many of its distinctive words appear in
        the alert display_name. Returns the id of the best match, or None.
        Generic HACCP/surveillance words are excluded from scoring to avoid false
        matches when all point names share a common suffix.
        """
        _STOP_WORDS = {'haccp', 'surveillance', 'humidite', 'humidité', 'alerte', 'hors', 'seuil'}
        alert_lower = (alert.display_name or '').lower()
        best_score = 0
        best_pid = None
        for point in points:
            words = [
                w for w in point.display_name.lower().split()
                if len(w) > 3 and w not in _STOP_WORDS
            ]
            score = sum(1 for w in words if w in alert_lower)
            if score > best_score:
                best_score = score
                best_pid = point.id
        return best_pid if best_score > 0 else None

    def _compute_frequency(self, checks):
        """Compute human-readable frequency from median interval between consecutive checks."""
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
