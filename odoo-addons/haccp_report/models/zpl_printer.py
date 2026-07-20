import socket


def _zpl_safe(text):
    """Retire les caractères réservés ZPL (^ et ~) pour éviter de corrompre
    l'étiquette si le texte contient un de ces caractères."""
    return str(text).replace('^', '').replace('~', '')


def build_zpl(reference, product_name, date_ouverture, operateur_name,
               date_limite, duree_jours, condition_label, portal_url):
    """Construit le ZPL pour l'étiquette DLC secondaire (format 62x38mm,
    imprimante OXHOO TLP200 compatible Zebra ZPL)."""
    return (
        '^XA\n'
        '^CF0,30\n'
        f'^FO20,20^FD{_zpl_safe(product_name)}^FS\n'
        '^CF0,20\n'
        f'^FO20,60^FDOuvert: {_zpl_safe(date_ouverture)}  Par: {_zpl_safe(operateur_name)}^FS\n'
        '^FO20,90^GB300,40,2^FS\n'
        '^CF0,28\n'
        f'^FO30,100^FDDLC: {_zpl_safe(date_limite)} (J+{duree_jours})^FS\n'
        f'^FO20,150^FDConservation: {_zpl_safe(condition_label)}^FS\n'
        f'^BY2^FO20,180^BCN,50,Y,N,N^FD{_zpl_safe(reference)}^FS\n'
        f'^FO250,150^BQN,2,4^FDQA,{_zpl_safe(portal_url)}^FS\n'
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
