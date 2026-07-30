import socket
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase

from odoo.addons.haccp_report.models.zpl_printer import build_zpl, send_zpl


class TestBuildZpl(TransactionCase):
    def test_contains_product_name_reference_and_lot(self):
        zpl = build_zpl(
            reference='2026-200-014',
            product_name='Sauce tomate maison',
            date_ouverture='19/07/2026',
            operateur_name='M. Dupont',
            date_limite='22/07/2026',
            duree_jours=3,
            condition_label='Réfrigéré (+4°C)',
            portal_url='http://192.168.1.182:8029/haccp/etiquette/42/abc123',
            lot_name='2026-200-014',
        )
        self.assertTrue(zpl.startswith('^XA'))
        self.assertTrue(zpl.rstrip().endswith('^XZ'))
        self.assertIn('Sauce tomate maison', zpl)
        self.assertIn('2026-200-014', zpl)
        self.assertIn('22/07/2026', zpl)
        self.assertIn('http://192.168.1.182:8029/haccp/etiquette/42/abc123', zpl)

    def test_aucun_code_barre_dans_le_zpl_genere(self):
        zpl = build_zpl(
            reference='2026-200-014', product_name='Sauce tomate maison',
            date_ouverture='19/07/2026', operateur_name='M. Dupont',
            date_limite='22/07/2026', duree_jours=3,
            condition_label='Réfrigéré (+4°C)', portal_url='http://example.com',
            lot_name='2026-200-014',
        )
        self.assertNotIn('^BCN', zpl)
        self.assertNotIn('^BY', zpl)

    def test_affiche_dlc_produit_origine_si_fournie(self):
        zpl = build_zpl(
            reference='ref', product_name='Sauce tomate maison',
            date_ouverture='19/07/2026', operateur_name='M. Dupont',
            date_limite='22/07/2026', duree_jours=3,
            condition_label='Réfrigéré (+4°C)', portal_url='http://example.com',
            lot_name='LOT-001', date_limite_produit_origine='30/07/2026',
        )
        self.assertIn('30/07/2026', zpl)

    def test_pas_de_ligne_dlc_origine_si_absente(self):
        zpl = build_zpl(
            reference='ref', product_name='Sauce tomate maison',
            date_ouverture='19/07/2026', operateur_name='M. Dupont',
            date_limite='22/07/2026', duree_jours=3,
            condition_label='Réfrigéré (+4°C)', portal_url='http://example.com',
            lot_name='LOT-001',
        )
        self.assertNotIn("DLC produit d'origine", zpl)

    def test_strips_reserved_zpl_characters_from_fields(self):
        zpl = build_zpl(
            reference='ref',
            product_name='Bœuf ^ légumes ~test',
            date_ouverture='19/07/2026',
            operateur_name='M. Dupont',
            date_limite='22/07/2026',
            duree_jours=3,
            condition_label='Réfrigéré (+4°C)',
            portal_url='http://example.com',
            lot_name='LOT-001',
        )
        self.assertNotIn('^ légumes', zpl)
        self.assertNotIn('~test', zpl)
        self.assertIn('Bœuf  légumes test', zpl)

    def test_declares_utf8_encoding_for_accented_characters(self):
        zpl = build_zpl(
            reference='ref', product_name='Réfrigéré', date_ouverture='19/07/2026',
            operateur_name='M. Dupont', date_limite='22/07/2026', duree_jours=3,
            condition_label='Réfrigéré (+4°C)', portal_url='http://example.com',
            lot_name='LOT-001',
        )
        self.assertIn('^CI28', zpl)
        self.assertTrue(zpl.index('^CI28') < zpl.index('^FD'))


class TestSendZpl(TransactionCase):
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
