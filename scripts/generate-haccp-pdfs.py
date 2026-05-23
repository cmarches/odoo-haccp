#!/usr/bin/env python3
"""Génère les 18 documents HACCP aux couleurs AIFluence Digital."""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Table, TableStyle, Spacer, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import KeepTogether

# ── Chemins ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.dirname(SCRIPT_DIR)
FONT_DIR   = "/tmp/aifd-branding/Geologica/static"
LOGO_WHITE = "/tmp/aifd-branding/logo_bluewhite.png"   # cyan + blanc — sur fond bleu nuit
LOGO_COLOR = "/tmp/aifd-branding/logo_blueblack.png"  # cyan + noir  — sur fond clair
OUT_DIR    = os.path.join(REPO_ROOT, "docs", "haccp-pdfs")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Charte graphique ─────────────────────────────────────────────────────────
ORANGE    = HexColor('#FAA223')
CYAN      = HexColor('#03B9E9')
BLEU_VIF  = HexColor('#0076E9')
BLEU_NUIT = HexColor('#0A1931')
GRIS      = HexColor('#333333')
GRIS_CLAIR= HexColor('#F5F5F5')
GRIS_BORD = HexColor('#DDDDDD')

W, H = A4   # 595 x 842 pt

# ── Polices ──────────────────────────────────────────────────────────────────
for weight, suffix in [
    ('Regular', 'Regular'), ('Bold', 'Bold'),
    ('Light', 'Light'), ('SemiBold', 'SemiBold'),
]:
    path = os.path.join(FONT_DIR, f"Geologica_Auto-{weight}.ttf")
    if os.path.exists(path):
        pdfmetrics.registerFont(TTFont(f"Geo-{suffix}", path))

# ── Styles texte ─────────────────────────────────────────────────────────────
def style(name, font='Geo-Regular', size=10, color=GRIS,
          align=TA_LEFT, space_before=0, space_after=4, leading=None):
    return ParagraphStyle(
        name, fontName=font, fontSize=size, textColor=color,
        alignment=align, spaceBefore=space_before,
        spaceAfter=space_after, leading=leading or size * 1.3,
    )

S_TITLE   = style('title',   'Geo-Bold',     18, white,    TA_LEFT,  0, 0)
S_CAT     = style('cat',     'Geo-Light',    10, CYAN,     TA_LEFT,  0, 0)
S_H1      = style('h1',      'Geo-Bold',     14, BLEU_NUIT,TA_LEFT,  12, 6)
S_H2      = style('h2',      'Geo-SemiBold', 11, BLEU_VIF, TA_LEFT,  10, 4)
S_BODY    = style('body',    'Geo-Regular',  10, GRIS,     TA_LEFT,  0,  4)
S_SMALL   = style('small',   'Geo-Light',     8, GRIS,     TA_LEFT,  0,  2)
S_CENTER  = style('center',  'Geo-Regular',  10, GRIS,     TA_CENTER,0,  4)
S_NOTE    = style('note',    'Geo-Light',     8, HexColor('#888888'), TA_LEFT, 6, 2)
S_STEP    = style('step',    'Geo-Bold',     12, white,    TA_CENTER, 0, 0)
S_STEP_TXT= style('steptxt', 'Geo-Regular',  10, GRIS,     TA_LEFT,  0,  4)
S_WARN    = style('warn',    'Geo-Bold',     11, ORANGE,   TA_LEFT,   4, 4)
S_FOOTER  = style('footer',  'Geo-Light',     7, HexColor('#999999'), TA_LEFT, 0, 0)

CATEGORIES = {
    'releves':         'Relevés & traçabilité',
    'affiches':        'Affiches de sensibilisation',
    'reglementation':  'Réglementation',
    'fiches_pratiques':'Fiches pratiques',
}

# ── Header / Footer (dessinés sur canvas) ─────────────────────────────────────
HEADER_H = 75
FOOTER_H = 30
MARGIN   = 20 * mm

def on_page(canvas, doc):
    canvas.saveState()
    # Header bleu nuit
    canvas.setFillColor(BLEU_NUIT)
    canvas.rect(0, H - HEADER_H, W, HEADER_H, fill=1, stroke=0)
    # Logo blanc
    try:
        canvas.drawImage(LOGO_WHITE, MARGIN, H - HEADER_H + 10,
                         width=120, height=50, preserveAspectRatio=True,
                         mask='auto')
    except Exception:
        pass
    # Barre orange verticale
    canvas.setFillColor(ORANGE)
    canvas.rect(W - MARGIN - 4, H - HEADER_H + 8, 4, HEADER_H - 16, fill=1, stroke=0)
    # Footer
    canvas.setStrokeColor(ORANGE)
    canvas.setLineWidth(1.5)
    canvas.line(MARGIN, FOOTER_H, W - MARGIN, FOOTER_H)
    canvas.setFont('Geo-Light', 7)
    canvas.setFillColor(HexColor('#999999'))
    canvas.drawString(MARGIN, FOOTER_H - 12, 'AIFluence Digital  •  Solutions HACCP')
    canvas.drawRightString(W - MARGIN, FOOTER_H - 12, 'aifluencedigital.com')
    canvas.setFont('Geo-Regular', 7)
    page_num = f"Page {canvas.getPageNumber()}"
    canvas.drawCentredString(W / 2, FOOTER_H - 12, page_num)
    canvas.restoreState()


def make_doc(filename, title, category):
    path = os.path.join(OUT_DIR, filename)
    doc = BaseDocTemplate(
        path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=HEADER_H + 10, bottomMargin=FOOTER_H + 18,
    )
    frame = Frame(
        MARGIN, FOOTER_H + 18,
        W - 2 * MARGIN, H - HEADER_H - FOOTER_H - 28,
        id='body',
    )
    tmpl = PageTemplate(id='main', frames=[frame], onPage=on_page)
    doc.addPageTemplates([tmpl])
    return doc, path


def draw_title(canvas, title, category):
    """Dessine titre + catégorie dans le header (appelé manuellement)."""
    cat_label = CATEGORIES.get(category, category)
    canvas.setFont('Geo-Light', 9)
    canvas.setFillColor(CYAN)
    canvas.drawString(MARGIN + 130, H - 25, cat_label.upper())
    canvas.setFont('Geo-Bold', 15)
    canvas.setFillColor(white)
    canvas.drawString(MARGIN + 130, H - 48, title)


def build_and_save(filename, title, category, story):
    doc, path = make_doc(filename, title, category)

    def on_page_with_title(c, d):
        on_page(c, d)
        draw_title(c, title, category)

    doc.pageTemplates[0].onPage = on_page_with_title
    doc.build(story)
    print(f"  ✓ {filename}")
    return path


# ── Helpers flowables ─────────────────────────────────────────────────────────
def section(title):
    return [
        Spacer(1, 6),
        Paragraph(title, S_H1),
        HRFlowable(width='100%', thickness=1, color=BLEU_VIF, spaceAfter=6),
    ]


def subsection(title):
    return [Paragraph(title, S_H2)]


def body(text):
    return Paragraph(text, S_BODY)


def note(text):
    return Paragraph(f"<i>{text}</i>", S_NOTE)


def warning(text):
    return Paragraph(f"⚠ {text}", S_WARN)


def table_style_base(header_rows=1):
    cmds = [
        ('BACKGROUND',  (0, 0), (-1, header_rows - 1), BLEU_NUIT),
        ('TEXTCOLOR',   (0, 0), (-1, header_rows - 1), white),
        ('FONTNAME',    (0, 0), (-1, header_rows - 1), 'Geo-Bold'),
        ('FONTSIZE',    (0, 0), (-1, header_rows - 1), 9),
        ('FONTNAME',    (0, header_rows), (-1, -1), 'Geo-Regular'),
        ('FONTSIZE',    (0, header_rows), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, header_rows), (-1, -1), [white, GRIS_CLAIR]),
        ('GRID',        (0, 0), (-1, -1), 0.5, GRIS_BORD),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',  (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]
    return TableStyle(cmds)


def colored_cell(text, bg, fg=white):
    style_c = ParagraphStyle('cc', fontName='Geo-Bold', fontSize=9,
                              textColor=fg, alignment=TA_CENTER)
    return Paragraph(text, style_c)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Fiche températures positives
# ═══════════════════════════════════════════════════════════════════════════════
def doc_temperatures_positives():
    story = []
    story += section("Contrôle des températures positives (+0°C à +5°C)")
    story.append(body("Objectif : vérifier quotidiennement que les équipements frigorifiques respectent la chaîne du froid réglementaire."))
    story.append(Spacer(1, 8))
    story += subsection("Seuils réglementaires")
    seuils = [
        ['Famille de produits', 'Température max'],
        ['Viande, volaille, charcuterie', '+4°C'],
        ['Poisson, produits de la mer', '+2°C'],
        ['Produits laitiers, œufs', '+4°C'],
        ['Fruits et légumes découpés', '+4°C'],
        ['Plats cuisinés, traiteur', '+3°C'],
    ]
    t = Table(seuils, colWidths=[340, 120])
    t.setStyle(table_style_base())
    story.append(t)
    story.append(Spacer(1, 12))
    story += subsection("Relevé journalier — Semaine du ___/___/______")
    header = ['Date', 'Heure', 'Frigo 1\n(°C)', 'Frigo 2\n(°C)', 'Frigo 3\n(°C)', 'Frigo 4\n(°C)', 'Action\ncorrective', 'Signature']
    rows = [header] + [['', '', '', '', '', '', '', ''] for _ in range(14)]
    col_w = [50, 40, 50, 50, 50, 50, 90, 65]
    t2 = Table(rows, colWidths=col_w, rowHeights=[22] + [18] * 14)
    t2.setStyle(table_style_base())
    t2.setStyle(TableStyle([
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (2, 0), (5, -1), 'CENTER'),
    ]))
    story.append(t2)
    story.append(Spacer(1, 8))
    story.append(note("Fréquence : 2 relevés/jour recommandés (ouverture et fermeture). En cas d'anomalie, noter l'action corrective et prévenir le responsable."))
    story.append(warning("Température hors seuil = non-conformité à traiter immédiatement."))
    return story


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Fiche températures négatives
# ═══════════════════════════════════════════════════════════════════════════════
def doc_temperatures_negatives():
    story = []
    story += section("Contrôle des températures négatives (−18°C)")
    story.append(body("Les produits surgelés doivent être conservés à −18°C ou moins. Tout écart supérieur à 3°C (−15°C) déclenche une non-conformité."))
    story.append(Spacer(1, 8))
    story += subsection("Seuils réglementaires congélateurs")
    seuils = [
        ['Type de produit', 'Température de conservation'],
        ['Produits surgelés (toutes familles)', '≤ −18°C'],
        ['Glaces et sorbets', '≤ −18°C'],
        ['Poisson congelé', '≤ −18°C'],
        ['Viande congelée', '≤ −18°C'],
    ]
    t = Table(seuils, colWidths=[340, 120])
    t.setStyle(table_style_base())
    story.append(t)
    story.append(Spacer(1, 12))
    story += subsection("Relevé journalier — Semaine du ___/___/______")
    header = ['Date', 'Heure', 'Congélo 1\n(°C)', 'Congélo 2\n(°C)', 'Congélo 3\n(°C)', 'Action\ncorrective', 'Signature']
    rows = [header] + [['', '', '', '', '', '', ''] for _ in range(14)]
    col_w = [55, 42, 65, 65, 65, 100, 63]
    t2 = Table(rows, colWidths=col_w, rowHeights=[22] + [18] * 14)
    t2.setStyle(table_style_base())
    story.append(t2)
    story.append(Spacer(1, 8))
    story.append(note("En cas de panne ou de coupure électrique, consulter la procédure 'Coupure électrique' et ne pas ouvrir les portes des congélateurs."))
    story.append(warning("Décongélation et recongélation interdites sans accord du responsable."))
    return story


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Registre allergènes
# ═══════════════════════════════════════════════════════════════════════════════
def doc_allergenes():
    story = []
    story += section("Registre des 14 allergènes majeurs")
    story.append(body("Règlement UE n°1169/2011 — Obligation d'information sur les allergènes pour toute denrée alimentaire vendue non préemballée."))
    story.append(Spacer(1, 8))
    allergenes = [
        ['N°', 'Allergène', 'Exemples de sources'],
        ['1',  'Gluten (céréales)',        'Blé, seigle, orge, avoine, épeautre, kamut'],
        ['2',  'Crustacés',                'Crevettes, homard, crabe, langoustine'],
        ['3',  'Œufs',                     'Ovoproduits, mayonnaise, pâtes aux œufs'],
        ['4',  'Poissons',                  'Anchois, cabillaud, saumon, thon, sardine'],
        ['5',  'Arachides',                 'Cacahuètes, huile d\'arachide, beurre de cacahuètes'],
        ['6',  'Soja',                      'Tofu, lécithine de soja, sauce soja, tempeh'],
        ['7',  'Lait',                      'Beurre, fromage, crème, yaourt, lactosérum'],
        ['8',  'Fruits à coque',            'Amandes, noisettes, noix, noix de cajou, pistaches'],
        ['9',  'Céleri',                    'Racine, graines, sel de céleri'],
        ['10', 'Moutarde',                  'Graines, farine, huile, condiments'],
        ['11', 'Graines de sésame',         'Tahini, huile de sésame, pain sésame'],
        ['12', 'Dioxyde de soufre / sulfites','Vins, vinaigre, fruits secs, conserves'],
        ['13', 'Lupin',                     'Farine de lupin, pâtes au lupin'],
        ['14', 'Mollusques',               'Huîtres, moules, coquilles St-Jacques, calmars'],
    ]
    col_w = [25, 140, 290]
    t = Table(allergenes, colWidths=col_w)
    t.setStyle(table_style_base())
    story.append(t)
    story.append(Spacer(1, 12))
    story += subsection("Déclaration par plat / produit")
    header2 = ['Nom du plat / produit'] + [str(i) for i in range(1, 15)]
    rows2 = [header2] + [[''] * 15 for _ in range(10)]
    col_w2 = [140] + [28] * 14
    t2 = Table(rows2, colWidths=col_w2, rowHeights=[22] + [16] * 10)
    t2.setStyle(table_style_base())
    t2.setStyle(TableStyle([('FONTSIZE', (0, 0), (-1, 0), 8), ('ALIGN', (1, 0), (-1, -1), 'CENTER')]))
    story.append(t2)
    story.append(note("Cocher (✓) la case si l'allergène est présent dans le plat. Mettre à jour à chaque changement de recette."))
    return story


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Affiche : Lavage des mains
# ═══════════════════════════════════════════════════════════════════════════════
def doc_lavage_mains():
    story = []
    story += section("Protocole de lavage des mains — 7 étapes obligatoires")
    story.append(warning("Lavage obligatoire : à l'arrivée, après les toilettes, après tout contact contaminant, avant manipulation d'aliments."))
    story.append(Spacer(1, 10))
    etapes = [
        ("1", "MOUILLER", "Ouvrir le robinet. Mouiller entièrement les mains et les poignets à l'eau courante tiède."),
        ("2", "SAVONNER", "Appliquer une dose de savon liquide (taille d'une pièce de 2€) sur toute la surface des mains."),
        ("3", "PAUMES", "Frotter les paumes l'une contre l'autre en effectuant des mouvements circulaires (15 secondes)."),
        ("4", "DOS", "Frotter le dos de chaque main avec la paume opposée, doigts entrelacés."),
        ("5", "DOIGTS", "Entrouvrir les doigts et frotter les espaces interdigitaux des deux côtés."),
        ("6", "POUCES & BOUTS", "Saisir chaque pouce dans la paume opposée et tourner. Frotter le bout des doigts sur la paume."),
        ("7", "RINCER & SÉCHER", "Rincer abondamment sous l'eau courante. Sécher avec un essuie-mains à usage unique. Fermer le robinet avec l'essuie-mains."),
    ]
    for num, titre, texte in etapes:
        row_data = [
            [colored_cell(num, ORANGE), colored_cell(titre, BLEU_NUIT), Paragraph(texte, S_BODY)]
        ]
        t = Table(row_data, colWidths=[35, 100, 320])
        t.setStyle(TableStyle([
            ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',  (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING',(0, 0),(-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND',  (0, 0), (0, 0),  ORANGE),
            ('BACKGROUND',  (1, 0), (1, 0),  GRIS_CLAIR),
            ('BOX',         (0, 0), (-1, -1), 0.5, GRIS_BORD),
        ]))
        story.append(t)
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 8))
    story.append(note("Durée totale minimum : 30 secondes. Le gel hydroalcoolique ne remplace pas le lavage des mains."))
    return story


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Affiche : Planches à découper
# ═══════════════════════════════════════════════════════════════════════════════
def doc_planches():
    story = []
    story += section("Code couleur des planches à découper")
    story.append(body("Pour éviter les contaminations croisées, chaque famille d'aliments dispose de sa propre planche identifiée par une couleur."))
    story.append(Spacer(1, 10))
    planches = [
        (HexColor('#CC0000'), white, "ROUGE",     "Viande crue",                "Bœuf, agneau, porc, veau crus"),
        (HexColor('#003399'), white, "BLEU",      "Poisson & fruits de mer",    "Poissons, crustacés, céphalopodes"),
        (HexColor('#006600'), white, "VERT",      "Légumes & fruits",           "Crudités, fruits, herbes fraîches"),
        (HexColor('#CCCC00'), GRIS,  "JAUNE",     "Volaille crue",              "Poulet, dinde, canard, pintade"),
        (HexColor('#F0F0F0'), GRIS,  "BLANC",     "Produits laitiers & pain",   "Fromage, beurre, pain, viennoiseries"),
        (HexColor('#663300'), white, "BRUN",      "Viande cuite & charcuterie", "Rôtis cuits, jambons, pâtés"),
    ]
    for bg, fg, couleur, famille, exemples in planches:
        row = [[colored_cell(couleur, bg, fg), Paragraph(f"<b>{famille}</b>", S_BODY), Paragraph(exemples, S_SMALL)]]
        t = Table(row, colWidths=[80, 180, 195])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 0.5, GRIS_BORD),
        ]))
        story.append(t)
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 8))
    story.append(warning("Nettoyage et désinfection obligatoires entre chaque famille d'aliments et en fin de service."))
    story.append(note("Remplacer les planches rayées ou usées : elles hébergent des bactéries dans les rainures."))
    return story


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Affiche : Chaîne du froid
# ═══════════════════════════════════════════════════════════════════════════════
def doc_chaine_froid():
    story = []
    story += section("La chaîne du froid — Températures réglementaires")
    story.append(body("La chaîne du froid est l'ensemble des moyens permettant de maintenir les aliments à leur température réglementaire, de la production jusqu'au consommateur."))
    story.append(Spacer(1, 8))
    temperatures = [
        ['Famille de produits', 'Conservation', 'Règle HACCP'],
        ['Poisson frais, crustacés', '0°C à +2°C', 'Rupture = élimination'],
        ['Viande, volaille crue', '0°C à +4°C', 'Rupture = élimination'],
        ['Produits laitiers, œufs', '0°C à +4°C', 'Contrôle DLC'],
        ['Charcuterie, traiteur', '0°C à +4°C', 'Contrôle DLC'],
        ['Légumes, fruits coupés', '0°C à +4°C', 'Consommer rapidement'],
        ['Denrées surgelées', '≤ −18°C', 'Décongélation interdit. sans protocole'],
        ['Plats chauds (service)', '≥ +63°C', 'Refroidissement < 2h si maintien'],
        ['Refroidissement rapide', '+63°C → +10°C', 'En moins de 2 heures'],
    ]
    t = Table(temperatures, colWidths=[195, 130, 130])
    t.setStyle(table_style_base())
    story.append(t)
    story.append(Spacer(1, 12))
    story += subsection("Zone de danger bactérien")
    danger = [
        ['Zone', 'Température', 'Risque'],
        ['Zone froide sûre',      '< 0°C',        'Développement arrêté'],
        ['Zone réfrigérée sûre',  '0°C à +4°C',   'Développement très lent'],
        ['Zone de danger',        '+4°C à +63°C',  '⚠ Multiplication rapide des bactéries'],
        ['Zone chaude sûre',      '> +63°C',       'Destruction des bactéries'],
    ]
    t2 = Table(danger, colWidths=[165, 130, 160])
    t2.setStyle(table_style_base())
    t2.setStyle(TableStyle([('BACKGROUND', (0, 3), (-1, 3), HexColor('#FFF3CD'))]))
    story.append(t2)
    story.append(warning("Ne jamais laisser des aliments entre +4°C et +63°C plus de 2 heures."))
    return story


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Affiche : Tenue d'hygiène
# ═══════════════════════════════════════════════════════════════════════════════
def doc_tenue():
    story = []
    story += section("Tenue d'hygiène — Équipements obligatoires en cuisine")
    story.append(body("Le port d'une tenue professionnelle complète est obligatoire pour toute personne intervenant en zone de préparation alimentaire (article 3 du règlement CE 852/2004)."))
    story.append(Spacer(1, 10))
    items = [
        ('Coiffe / toque', 'Obligatoire',
         "Couvre l'intégralité des cheveux. Portée dès l'entrée en cuisine. Changée quotidiennement."),
        ('Veste ou blouse blanche', 'Obligatoire',
         "Propre à chaque prise de poste. Réservée au travail — ne pas sortir avec la tenue."),
        ('Tablier', 'Selon poste',
         "Tablier plastifié pour la découpe, tablier tissu pour la préparation. Changé en cas de souillure."),
        ('Pantalon de cuisine', 'Obligatoire',
         "Tissu résistant, de couleur claire pour détecter les souillures."),
        ('Chaussures de sécurité', 'Obligatoire',
         "Fermées, antidérapantes, résistantes aux huiles. Réservées à l'usage professionnel."),
        ('Gants à usage unique', 'Selon tâche',
         "Changés entre chaque tâche. Ne remplacent pas le lavage des mains. Latex/nitrile selon allergies."),
        ('Masque / visière', 'Si prescrit',
         "Obligatoire en cas de pathologie ORL ou selon les protocoles internes."),
    ]
    for equip, obligation, detail in items:
        if obligation == 'Obligatoire':
            badge_bg, badge_fg = HexColor('#006600'), white
        elif obligation == 'Selon poste':
            badge_bg, badge_fg = BLEU_VIF, white
        else:
            badge_bg, badge_fg = GRIS_BORD, GRIS
        row = [[colored_cell(obligation, badge_bg, badge_fg),
                Paragraph(f"<b>{equip}</b>", S_BODY),
                Paragraph(detail, S_SMALL)]]
        t = Table(row, colWidths=[75, 130, 250])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 0.5, GRIS_BORD),
        ]))
        story.append(t)
        story.append(Spacer(1, 3))
    story.append(Spacer(1, 8))
    story.append(note("Bijoux, montres et ongles vernis sont interdits en zone alimentaire. Les plaies doivent être couvertes d'un pansement bleu détectable."))
    return story


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Fiche recette
# ═══════════════════════════════════════════════════════════════════════════════
def doc_fiche_recette():
    story = []
    story += section("Modèle de fiche recette — Avec déclaration allergènes")
    identite = [
        ['Nom de la recette', '', 'Catégorie', ''],
        ['Nb de couverts', '', 'DLC après prépa', ''],
        ['Responsable', '', 'Date création', ''],
    ]
    t = Table(identite, colWidths=[110, 120, 110, 115])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Geo-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Geo-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, GRIS_BORD),
        ('BACKGROUND', (0, 0), (0, -1), GRIS_CLAIR),
        ('BACKGROUND', (2, 0), (2, -1), GRIS_CLAIR),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))
    story += subsection("Ingrédients")
    ingr_h = [['Ingrédient', 'Quantité', 'Unité', 'Fournisseur', 'Allergènes']]
    ingr_r = [['', '', '', '', ''] for _ in range(10)]
    t2 = Table(ingr_h + ingr_r, colWidths=[155, 60, 50, 130, 60])
    t2.setStyle(table_style_base())
    story.append(t2)
    story.append(Spacer(1, 10))
    story += subsection("Préparation")
    prep_h = [['Étape', 'Description', 'T° / Durée', 'CCP ?']]
    prep_r = [[str(i), '', '', '☐'] for i in range(1, 7)]
    t3 = Table(prep_h + prep_r, colWidths=[40, 300, 90, 45])
    t3.setStyle(table_style_base())
    story.append(t3)
    story.append(Spacer(1, 10))
    story += subsection("Déclaration allergènes (cocher si présent)")
    al_labels = ['Gluten', 'Crustacés', 'Œufs', 'Poisson', 'Arachides', 'Soja', 'Lait',
                 'Fruits à\ncoque', 'Céleri', 'Moutarde', 'Sésame', 'Sulfites', 'Lupin', 'Mollusques']
    al_row = [[Paragraph(f"☐ {l}", S_SMALL) for l in al_labels]]
    t4 = Table(al_row, colWidths=[37] * 14)
    t4.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, GRIS_BORD),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t4)
    story.append(note("CCP = Point Critique de Contrôle. Indiquer la température et durée si cuisson, refroidissement ou maintien en température."))
    return story


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Affiche : Coupure électrique
# ═══════════════════════════════════════════════════════════════════════════════
def doc_coupure_electrique():
    story = []
    story += section("Procédure coupure électrique — Équipements frigorifiques")
    story.append(warning("En cas de coupure électrique, NE PAS OUVRIR les portes des réfrigérateurs et congélateurs."))
    story.append(Spacer(1, 8))
    etapes = [
        ("0-30 min", "NE PAS OUVRIR",
         "Un réfrigérateur fermé maintient sa température 2h, un congélateur 24 à 48h selon son contenu. Ne pas ouvrir les portes."),
        ("Immédiatement", "ALERTER",
         "Prévenir le responsable ou le gérant. Contacter le gestionnaire de l'immeuble / l'électricien. Appeler le service technique du matériel si nécessaire."),
        ("Dès la reprise", "CONTRÔLER",
         "Vérifier et noter la température de chaque appareil. Si < 4°C pour les positifs et < −15°C pour les négatifs : denrées conformes."),
        ("Si hors seuil", "ÉVALUER",
         "Evaluer le temps passé hors température. Consulter le tableau ci-dessous. En cas de doute, jeter plutôt que risquer une intoxication."),
        ("Toujours", "ENREGISTRER",
         "Compléter le registre des non-conformités : date, heure début/fin, appareils concernés, températures relevées, décision prise, signataire."),
    ]
    for timing, action, texte in etapes:
        row = [[colored_cell(timing, BLEU_NUIT), colored_cell(action, ORANGE), Paragraph(texte, S_BODY)]]
        t = Table(row, colWidths=[75, 100, 280])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 0.5, GRIS_BORD),
        ]))
        story.append(t)
        story.append(Spacer(1, 3))
    story.append(Spacer(1, 10))
    story += subsection("Décision selon durée et famille de produits")
    decision = [
        ['Produit', '< 2h hors T°', '2h à 4h hors T°', '> 4h hors T°'],
        ['Viande, volaille, poisson crus', 'Garder', 'Utiliser immédiatement', 'Éliminer'],
        ['Produits laitiers, œufs',        'Garder', 'Vérifier odeur/aspect',  'Éliminer si doute'],
        ['Plats cuisinés, traiteur',        'Garder', 'Chauffer immédiatement', 'Éliminer'],
        ['Surgelés (congélo)',              'Garder', 'Garder (si encore froid)', 'Ne pas recongeler'],
    ]
    t2 = Table(decision, colWidths=[155, 80, 130, 90])
    t2.setStyle(table_style_base())
    story.append(t2)
    return story


# ═══════════════════════════════════════════════════════════════════════════════
# 10–12. Réglementations (template générique)
# ═══════════════════════════════════════════════════════════════════════════════
def doc_reglementation(titre, reference, objet, articles_cles, obligations):
    story = []
    story += section(f"Résumé réglementaire — {reference}")
    story.append(body(f"<b>Objet :</b> {objet}"))
    story.append(Spacer(1, 8))
    story += subsection("Articles clés")
    for art, desc in articles_cles:
        story.append(body(f"<b>{art} :</b> {desc}"))
    story.append(Spacer(1, 10))
    story += subsection("Obligations pour les exploitants du secteur alimentaire")
    for obl in obligations:
        story.append(body(f"• {obl}"))
    story.append(Spacer(1, 10))
    story.append(note("Document de synthèse AIFluence Digital — Se référer au texte officiel publié au Journal Officiel de l'UE / JORF pour application réglementaire."))
    return story


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Cerfa 12211-02
# ═══════════════════════════════════════════════════════════════════════════════
def doc_cerfa():
    story = []
    story += section("Déclaration d'établissement — Cerfa n°12211-02")
    story.append(body("Ce formulaire est à adresser à la Direction Départementale de Protection des Populations (DDPP) avant l'ouverture de tout établissement du secteur alimentaire."))
    story.append(Spacer(1, 8))
    story += subsection("Identification de l'établissement")
    champs = [
        ['Raison sociale / Nom', ''],
        ['SIRET', ''],
        ['Adresse complète', ''],
        ['Code postal', '                  Commune : '],
        ['Téléphone', '                  Email : '],
        ['Nom du responsable', ''],
    ]
    t = Table(champs, colWidths=[180, 275])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Geo-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, GRIS_BORD),
        ('BACKGROUND', (0, 0), (0, -1), GRIS_CLAIR),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))
    story += subsection("Nature de l'activité")
    activites = [
        '☐  Restauration traditionnelle', '☐  Restauration rapide',
        '☐  Restauration collective', '☐  Traiteur / livraison',
        '☐  Boulangerie / pâtisserie', '☐  Boucherie / charcuterie',
        '☐  Épicerie / commerce de détail', '☐  Autre : ___________________',
    ]
    for i in range(0, len(activites), 2):
        row = [[Paragraph(activites[i], S_BODY), Paragraph(activites[i+1] if i+1 < len(activites) else '', S_BODY)]]
        t2 = Table(row, colWidths=[228, 227])
        t2.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        story.append(t2)
    story.append(Spacer(1, 10))
    story += subsection("Signature et envoi")
    story.append(body("À adresser par courrier recommandé AR à votre DDPP ou DDETSPP, ou déposer en ligne sur le portail des démarches administratives."))
    sign = [['Fait à : ___________________', 'Le : ___/___/______', 'Signature + cachet :']]
    t3 = Table(sign, colWidths=[180, 120, 155])
    t3.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, GRIS_BORD),
        ('TOPPADDING', (0, 0), (-1, -1), 20),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    story.append(t3)
    story.append(note("Ce formulaire est une aide à la rédaction basée sur le Cerfa 12211-02. Télécharger le formulaire officiel sur service-public.fr."))
    return story


# ═══════════════════════════════════════════════════════════════════════════════
# 14–18. Fiches pratiques METRO (template générique)
# ═══════════════════════════════════════════════════════════════════════════════
def doc_metro(titre, introduction, sections_content):
    story = []
    story += section(titre)
    story.append(body(introduction))
    story.append(Spacer(1, 8))
    for sec_title, items in sections_content:
        story += subsection(sec_title)
        for item in items:
            if isinstance(item, str):
                story.append(body(f"• {item}"))
            else:
                story.append(item)
        story.append(Spacer(1, 6))
    story.append(note("Document pédagogique AIFluence Digital inspiré des bonnes pratiques d'hygiène en restauration. Pour aller plus loin : formation HACCP certifiée."))
    return story


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — Génération des 18 PDFs
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    print("Génération des PDFs HACCP — AIFluence Digital")
    print("=" * 50)

    # 1. Fiche températures positives
    build_and_save(
        'AIFD-fiche-temperatures-positives.pdf',
        'Fiche températures positives',
        'releves',
        doc_temperatures_positives()
    )

    # 2. Fiche températures négatives
    build_and_save(
        'AIFD-fiche-temperatures-negatives.pdf',
        'Fiche températures négatives',
        'releves',
        doc_temperatures_negatives()
    )

    # 3. Registre allergènes
    build_and_save(
        'AIFD-registre-allergenes.pdf',
        'Registre allergènes',
        'releves',
        doc_allergenes()
    )

    # 4. Lavage des mains
    build_and_save(
        'AIFD-affiche-lavage-mains.pdf',
        'Lavage des mains — 7 étapes',
        'affiches',
        doc_lavage_mains()
    )

    # 5. Planches à découper
    build_and_save(
        'AIFD-affiche-planches-decoupe.pdf',
        'Planches à découper — Code couleur',
        'affiches',
        doc_planches()
    )

    # 6. Chaîne du froid
    build_and_save(
        'AIFD-affiche-chaine-froid.pdf',
        'Chaîne du froid',
        'affiches',
        doc_chaine_froid()
    )

    # 7. Tenue d'hygiène
    build_and_save(
        'AIFD-affiche-tenue-hygiene.pdf',
        "Tenue d'hygiène",
        'affiches',
        doc_tenue()
    )

    # 8. Fiche recette
    build_and_save(
        'AIFD-affiche-fiche-recette.pdf',
        'Fiche recette avec allergènes',
        'affiches',
        doc_fiche_recette()
    )

    # 9. Coupure électrique
    build_and_save(
        'AIFD-affiche-coupure-electrique.pdf',
        'Coupure électrique — Procédure',
        'affiches',
        doc_coupure_electrique()
    )

    # 10. Décret 0043
    build_and_save(
        'AIFD-decret-0043-2024.pdf',
        'Décret 0043 (02/2024)',
        'reglementation',
        doc_reglementation(
            'Décret 0043 (02/2024)',
            'Décret n°0043 du 12 février 2024',
            "Normes sanitaires applicables aux établissements de restauration collective et commerciale.",
            [
                ("Art. 1", "Champ d'application : tout établissement préparant ou distribuant des denrées alimentaires à des tiers."),
                ("Art. 3", "Obligation de formation HACCP pour au moins un responsable par établissement."),
                ("Art. 5", "Enregistrement des autocontrôles — conservation des documents pendant 3 ans minimum."),
                ("Art. 7", "Traçabilité amont et aval obligatoire pour toutes les denrées d'origine animale."),
                ("Art. 9", "Déclaration préalable d'activité auprès de la DDPP (Cerfa 12211-02)."),
            ],
            [
                "Former au moins un salarié à la méthode HACCP (formation de 14h minimum reconnue).",
                "Tenir un plan de maîtrise sanitaire (PMS) à jour et disponible pour tout contrôle.",
                "Effectuer et enregistrer des autocontrôles bactériologiques selon la fréquence définie.",
                "Garantir la traçabilité des matières premières (bons de livraison conservés 3 ans).",
                "Déclarer tout changement d'activité ou de responsable à la DDPP dans les 30 jours.",
                "Afficher les résultats des contrôles officiels (Alim'confiance) en façade ou en caisse.",
            ]
        )
    )

    # 11. Règlement CE 178/2002
    build_and_save(
        'AIFD-reglement-ce-178-2002.pdf',
        'Règlement CE 178/2002',
        'reglementation',
        doc_reglementation(
            'Règlement CE 178/2002',
            'Règlement (CE) n°178/2002 du Parlement européen',
            "Établit les principes généraux et les prescriptions générales de la législation alimentaire, institue l'Autorité européenne de sécurité des aliments (EFSA).",
            [
                ("Art. 14", "Les denrées alimentaires ne doivent pas être mises sur le marché si elles sont dangereuses."),
                ("Art. 17", "Responsabilité des exploitants : vérifier que les denrées satisfont aux exigences législatives."),
                ("Art. 18", "Traçabilité : capacité à retracer la chaîne alimentaire à tous les stades."),
                ("Art. 19", "Retrait des denrées non conformes — obligation d'information des autorités."),
                ("Art. 20", "Responsabilité des exploitants du secteur de l'alimentation animale."),
            ],
            [
                "Garantir la sécurité de toutes les denrées mises sur le marché.",
                "Maintenir un système de traçabilité complet (fournisseurs + clients directs).",
                "Retirer et rappeler immédiatement toute denrée non conforme.",
                "Informer les autorités compétentes (DDPP) en cas de risque pour la santé.",
                "Coopérer avec les autorités lors des inspections et contrôles officiels.",
            ]
        )
    )

    # 12. Règlement CE 852/2004
    build_and_save(
        'AIFD-reglement-ce-852-2004.pdf',
        'Règlement CE 852/2004',
        'reglementation',
        doc_reglementation(
            'Règlement CE 852/2004',
            'Règlement (CE) n°852/2004 — Hygiène des denrées alimentaires',
            "Fixe les exigences générales en matière d'hygiène applicables à toutes les étapes de la production, de la transformation et de la distribution des denrées alimentaires.",
            [
                ("Annexe II — Ch. 1", "Locaux : conception, aménagement permettant le nettoyage et la désinfection."),
                ("Annexe II — Ch. 5", "Exigences applicables aux équipements (matériaux lisses, lavables, non toxiques)."),
                ("Annexe II — Ch. 8", "Hygiène personnelle : interdiction du travail aux personnes présentant une maladie contagieuse."),
                ("Art. 5", "Mise en place de procédures basées sur les principes HACCP."),
                ("Art. 6", "Contrôles officiels — enregistrements mis à disposition des autorités."),
            ],
            [
                "Mettre en place un Plan de Maîtrise Sanitaire (PMS) basé sur les 7 principes HACCP.",
                "Concevoir et entretenir les locaux pour faciliter le nettoyage et éviter la contamination croisée.",
                "Maintenir les équipements en bon état, propres et désinfectés selon le plan de nettoyage.",
                "Former le personnel aux règles d'hygiène personnelle et au port de la tenue réglementaire.",
                "Contrôler régulièrement l'eau utilisée (potable) et la qualité microbiologique des surfaces.",
                "Conserver les enregistrements (températures, nettoyage, autocontrôles) pendant au moins 3 ans.",
            ]
        )
    )

    # 13. Cerfa 12211-02
    build_and_save(
        'AIFD-cerfa-12211-02.pdf',
        'Cerfa 12211-02 — Déclaration établissement',
        'reglementation',
        doc_cerfa()
    )

    # 14. METRO Hygiène n°3
    build_and_save(
        'AIFD-hygiene-3.pdf',
        'Fiche pratique hygiène n°3',
        'fiches_pratiques',
        doc_metro(
            "Nettoyage & Désinfection — Bonnes pratiques",
            "Le nettoyage élimine les salissures visibles. La désinfection détruit les micro-organismes. Les deux étapes sont indispensables et doivent être réalisées dans cet ordre.",
            [
                ("Les 5 étapes du nettoyage-désinfection", [
                    "Débarrasser et pré-nettoyer (retirer les gros déchets à sec)",
                    "Rincer à l'eau chaude (>45°C) pour solubiliser les graisses",
                    "Appliquer le détergent et laisser agir selon le temps de contact indiqué",
                    "Rincer abondamment à l'eau potable pour éliminer le détergent",
                    "Appliquer le désinfectant (laisser agir) puis rincer si requis",
                ]),
                ("Produits et dosages", [
                    "Utiliser uniquement des produits homologués pour le secteur alimentaire.",
                    "Respecter scrupuleusement les dilutions prescrites (dosage ≠ efficacité).",
                    "Ne jamais mélanger deux produits chimiques différents.",
                    "Stocker les produits dans leur emballage d'origine, hors zone alimentaire.",
                ]),
                ("Fréquences minimales recommandées", [
                    Table([
                        ['Surface', 'Fréquence'],
                        ['Plans de travail', 'Après chaque utilisation'],
                        ['Équipements (robot, trancheur)', 'Quotidien'],
                        ['Sols', 'Quotidien'],
                        ['Murs, portes', 'Hebdomadaire'],
                        ['Hottes, filtres', 'Mensuel'],
                    ], colWidths=[200, 200],
                    style=table_style_base()),
                ]),
            ]
        )
    )

    # 15. METRO Hygiène n°4
    build_and_save(
        'AIFD-hygiene-4.pdf',
        'Fiche pratique hygiène n°4',
        'fiches_pratiques',
        doc_metro(
            "Gestion des déchets — Règles et bonnes pratiques",
            "Une mauvaise gestion des déchets est l'une des premières causes de contamination en cuisine. Les déchets alimentaires attirent les nuisibles et propagent les bactéries.",
            [
                ("Les différents flux de déchets", [
                    "Déchets alimentaires (restes, épluchures) : tri et élimination fréquente",
                    "Emballages souillés : sac poubelle hermétique, évacuation régulière",
                    "Huiles usagées : collecte séparée obligatoire (filière agréée)",
                    "Déchets dangereux (produits chimiques) : collecte spécialisée",
                ]),
                ("Règles d'or", [
                    "Poubelles avec couvercle à pédale (pas de contact main/couvercle).",
                    "Sacs poubelle : changer au minimum 2 fois par jour et dès que plein au 3/4.",
                    "Nettoyer et désinfecter les poubelles à chaque changement de sac.",
                    "Zone de stockage des déchets : séparée de la zone alimentaire, ventilée, facile à nettoyer.",
                    "Évacuation des déchets avant fermeture et au minimum toutes les 24h.",
                ]),
                ("Obligations réglementaires", [
                    "Volume de déchets > 100 kg/semaine : convention avec un prestataire agréé.",
                    "Huiles de friture : bordereau de suivi obligatoire (arrêté du 18/08/1999).",
                    "Traçabilité des déchets d'origine animale (DAOA) : registre tenu à jour.",
                ]),
            ]
        )
    )

    # 16. METRO Hygiène n°5
    build_and_save(
        'AIFD-hygiene-5.pdf',
        'Fiche pratique hygiène n°5',
        'fiches_pratiques',
        doc_metro(
            "Lutte contre les nuisibles (3D : Dératisation, Désinsectisation, Désinfection)",
            "La présence de nuisibles (rongeurs, insectes, oiseaux) dans un établissement alimentaire est une non-conformité grave pouvant entraîner la fermeture administrative.",
            [
                ("Principaux nuisibles et risques", [
                    Table([
                        ['Nuisible', 'Risques', 'Signes de présence'],
                        ['Rongeurs (rats, souris)', 'Salmonellose, leptospirose', 'Crottes, morsures, grignotages'],
                        ['Blattes', 'Contamination alimentaire', 'Odeur, excréments, traces'],
                        ['Mouches, moustiques', 'Transmission de pathogènes', 'Présence visuelle'],
                        ['Oiseaux', 'Salmonellose, campylobacter', 'Fientes, plumes, nids'],
                    ], colWidths=[130, 150, 175],
                    style=table_style_base()),
                ]),
                ("Mesures préventives", [
                    "Colmater toutes les ouvertures > 5 mm (joints, grilles, siphons).",
                    "Installer des moustiquaires sur toutes les ouvertures (fenêtres, aérations).",
                    "Stocker les denrées dans des contenants hermétiques, surélevés du sol.",
                    "Éliminer les sources d'eau stagnante (siphons, infiltrations).",
                    "Vider et nettoyer les poubelles quotidiennement.",
                ]),
                ("Plan de lutte", [
                    "Désigner un responsable 3D dans l'établissement.",
                    "Contrat avec un prestataire 3D certifié Biocide (renouvellement annuel recommandé).",
                    "Carnet de suivi 3D tenu à jour, disponible lors des contrôles officiels.",
                    "Signaler immédiatement toute présence de nuisibles au responsable.",
                ]),
            ]
        )
    )

    # 17. METRO Plan nettoyage
    build_and_save(
        'AIFD-plan-nettoyage.pdf',
        'Plan de nettoyage hebdomadaire',
        'fiches_pratiques',
        doc_metro(
            "Plan de nettoyage et désinfection — Modèle hebdomadaire",
            "Ce plan liste les tâches de nettoyage à effectuer par zone et par fréquence. À adapter selon la taille et l'activité de votre établissement.",
            [
                ("Planning hebdomadaire", [
                    Table([
                        ['Zone / Équipement', 'Produit', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
                        ['Plans de travail', 'Détergent-désinfectant', '☐','☐','☐','☐','☐','☐','☐'],
                        ['Sols cuisine', 'Dégraissant', '☐','☐','☐','☐','☐','☐','☐'],
                        ['Réfrigérateurs', 'Détergent alimentaire', '','','','','☐','',''],
                        ['Congélateurs', 'Détergent alimentaire', '','','','','','☐',''],
                        ['Hottes & filtres', 'Dégraissant puissant', '','','','','','','☐'],
                        ['Sols chambre froide', 'Dégraissant', '☐','☐','☐','☐','☐','☐','☐'],
                        ['Murs & carrelages', 'Détergent-désinfectant', '','','☐','','','☐',''],
                        ['Poubelles', 'Désinfectant', '☐','☐','☐','☐','☐','☐','☐'],
                        ['Vestiaires & WC', 'Désinfectant sanitaire', '☐','☐','☐','☐','☐','☐','☐'],
                    ], colWidths=[145, 105, 28, 28, 28, 28, 28, 28, 28],
                    style=table_style_base()),
                ]),
                ("Visa hebdomadaire", [
                    Table([
                        ['Semaine du', 'Responsable', 'Visa', 'Observations'],
                        ['___/___/______', '', '', ''],
                        ['___/___/______', '', '', ''],
                        ['___/___/______', '', '', ''],
                    ], colWidths=[110, 130, 60, 155],
                    style=table_style_base()),
                ]),
            ]
        )
    )

    # 18. METRO Plan nettoyage durable
    build_and_save(
        'AIFD-plan-nettoyage-durable.pdf',
        'Plan nettoyage éco-responsable',
        'fiches_pratiques',
        doc_metro(
            "Nettoyage éco-responsable — Produits & pratiques durables",
            "Adopter des pratiques de nettoyage durables réduit l'impact environnemental et les coûts, tout en maintenant le niveau d'hygiène réglementaire.",
            [
                ("Critères de sélection des produits éco-responsables", [
                    "Label Ecolabel européen ou NF Environnement pour les produits de nettoyage.",
                    "Concentration élevée : privilégier les formats concentrés (moins d'emballages, moins de transport).",
                    "Sans phosphates, sans chlore actif si possible (risque aquatique).",
                    "Biodégradabilité > 90% selon OCDE 301 ou équivalent.",
                    "Fournisseur local si possible pour réduire l'empreinte carbone.",
                ]),
                ("Pratiques économes en eau et énergie", [
                    "Nettoyage à sec en première passe pour éliminer les grosses souillures avant le mouillage.",
                    "Régler la pression d'eau (jet trop fort = gaspillage et projection de contamination).",
                    "Utiliser des raclettes et balais-poussiéreux avant lavage des sols.",
                    "Préparer les solutions à la dose exacte préconisée (trop = pollution, trop peu = inefficace).",
                    "Préférer l'eau chaude uniquement quand nécessaire (graisses) — eau froide suffit pour beaucoup.",
                ]),
                ("Comparatif produits conventionnels vs éco", [
                    Table([
                        ['Usage', 'Produit conventionnel', 'Alternative éco'],
                        ['Dégraissant plans de travail', 'Produit base soude', 'Bicarbonate + savon noir'],
                        ['Désinfectant surfaces', 'Ammonium quaternaire', 'Acide peracétique dilué'],
                        ['Sols', 'Détergent alcalin', 'Ecolabel certifié neutre'],
                        ['Vitres', 'Alcool isopropylique', 'Vinaigre blanc dilué + microfibre'],
                        ['WC / sanitaires', 'Chlore actif', 'Acide citrique + label'],
                    ], colWidths=[145, 155, 155],
                    style=table_style_base()),
                ]),
            ]
        )
    )

    print("=" * 50)
    print(f"✓ 18 PDFs générés dans : {OUT_DIR}")


if __name__ == '__main__':
    main()
