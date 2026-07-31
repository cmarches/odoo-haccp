import socket


def _zpl_safe(text):
    """Retire les caractères réservés ZPL (^ et ~) pour éviter de corrompre
    l'étiquette si le texte contient un de ces caractères."""
    return str(text).replace('^', '').replace('~', '')


def build_zpl(reference, product_name, date_ouverture, operateur_name,
               date_limite, duree_jours, condition_label, portal_url,
               lot_name, date_limite_produit_origine=None):
    """Construit le ZPL pour l'étiquette DLC secondaire (imprimante OXHOO
    TLP200 compatible Zebra ZPL, étiquette 99x80mm @ 203dpi = 792x640 dots).

    ^CI28 déclare l'encodage UTF-8 pour que les accents (é, à...) s'impriment
    correctement — sans cette commande le firmware Zebra interprète le texte
    avec son codepage par défaut et corrompt les caractères accentués.

    ^PW/^LL déclarent explicitement les dimensions du canevas en dots plutôt
    que de dépendre de la config mémorisée par l'imprimante, pour que les
    coordonnées ci-dessous correspondent réellement à la taille physique de
    l'étiquette.

    Pas de code-barre : aucun processus du système ne le lit (la clôture
    d'étiquette se fait par scan du QR, pas par recherche de référence) —
    référence et lot sont affichés en texte simple. Le QR reste le seul
    élément scanné, conservé à sa position d'origine.

    "DLC produit d'origine: <date>" sur une seule ligne (~34 caractères)
    chevauchait le QR à l'impression physique réelle -- "Référence: ..."
    (~23 caractères, même position/police) avait été confirmée sans
    chevauchement, donc le libellé seul est mis sur cette longueur validée
    en renvoyant la date à la ligne suivante. Le QR est aussi décalé de
    64 dots (8mm @ 203dpi) vers la droite en marge de sécurité
    supplémentaire."""
    origine_line = ''
    if date_limite_produit_origine:
        origine_line = (
            "^FO40,410^FDDLC produit d'origine:^FS\n"
            f"^FO40,445^FD{_zpl_safe(date_limite_produit_origine)}^FS\n"
        )
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
        f'^FO40,320^FDRéférence: {_zpl_safe(reference)}^FS\n'
        f'^FO40,355^FDLot: {_zpl_safe(lot_name)}^FS\n'
        f'{origine_line}'
        f'^FO524,320^BQN,2,5^FDQA,{_zpl_safe(portal_url)}^FS\n'
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
