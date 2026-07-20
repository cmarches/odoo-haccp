import socket


def _zpl_safe(text):
    """Retire les caractères réservés ZPL (^ et ~) pour éviter de corrompre
    l'étiquette si le texte contient un de ces caractères."""
    return str(text).replace('^', '').replace('~', '')


def build_zpl(reference, product_name, date_ouverture, operateur_name,
               date_limite, duree_jours, condition_label, portal_url):
    """Construit le ZPL pour l'étiquette DLC secondaire (imprimante OXHOO
    TLP200 compatible Zebra ZPL, étiquette 99x80mm @ 203dpi = 792x640 dots).

    ^CI28 déclare l'encodage UTF-8 pour que les accents (é, à...) s'impriment
    correctement — sans cette commande le firmware Zebra interprète le texte
    avec son codepage par défaut et corrompt les caractères accentués.

    ^PW/^LL déclarent explicitement les dimensions du canevas en dots plutôt
    que de dépendre de la config mémorisée par l'imprimante, pour que les
    coordonnées ci-dessous correspondent réellement à la taille physique de
    l'étiquette.

    Le code-barre (^BY2, ~360 dots de large max pour une référence type
    AAAA-JJJ-NNN) et le QR sont placés côte à côte sur la même ligne, avec
    une marge large entre les deux, plutôt qu'empilés verticalement — la
    taille réelle du QR dépend de la longueur de l'URL encodée (référence +
    token) et peut dépasser la hauteur du code-barre, donc les empiler
    créait un chevauchement quelle que soit cette taille."""
    return (
        '^XA\n'
        '^CI28\n'
        '^PW792\n'
        '^LL640\n'
        '^CF0,50\n'
        f'^FO40,50^FD{_zpl_safe(product_name)}^FS\n'
        '^CF0,32\n'
        f'^FO40,120^FDOuvert: {_zpl_safe(date_ouverture)}  Par: {_zpl_safe(operateur_name)}^FS\n'
        '^FO40,175^GB712,4,4^FS\n'
        '^CF0,48\n'
        f'^FO40,205^FDDLC: {_zpl_safe(date_limite)} (J+{duree_jours})^FS\n'
        '^CF0,32\n'
        f'^FO40,275^FDConservation: {_zpl_safe(condition_label)}^FS\n'
        f'^BY2^FO40,340^BCN,100,Y,N,N^FD{_zpl_safe(reference)}^FS\n'
        f'^FO460,320^BQN,2,5^FDQA,{_zpl_safe(portal_url)}^FS\n'
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
