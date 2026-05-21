# Spec — Module Odoo `haccp_report` : Rapport HACCP DDPP

**Date :** 2026-05-21
**Statut :** Approuvé — prêt pour implémentation
**Auteur :** Brainstorming AIFluence Digital
**Périmètre :** Module Odoo addons — rapport PDF réglementaire HACCP à destination des contrôles DDPP

---

## 1. Contexte et objectifs

### 1.1 Contexte réglementaire

La DDPP (Direction Départementale de la Protection des Populations) peut demander à tout moment les relevés de surveillance HACCP d'un établissement de restauration. Le Règlement CE 852/2004 (Article 5) impose :
- La mise en place d'un système HACCP documenté
- L'enregistrement de toutes les mesures aux Points Critiques de Contrôle (CCP)
- La traçabilité des non-conformités et actions correctives
- L'archivage des enregistrements pendant **3 ans minimum**

### 1.2 Objectif du module

Produire, à la demande, un rapport PDF réglementaire compilant toutes les données de surveillance IoT enregistrées dans Odoo sur une période donnée. Le rapport doit être immédiatement présentable à un inspecteur DDPP.

### 1.3 Compatibilité

Le module fonctionne sur **Odoo 19 CE et EE** sans modification.
- Développement et affinage layout : Odoo 19 EE (192.168.1.182:8029, base `odoo19e_dev`)
- Déploiement production client : Odoo 19 CE (VPS Hetzner ~5€/mois)
- Studio EE peut être utilisé pour retoucher le template QWeb après déploiement sans redéploiement

---

## 2. Architecture du module

### 2.1 Nom et dépendances

```
Nom technique : haccp_report
Version       : 19.0.1.0.0
Dépendances   : ['quality_control', 'web']
```

### 2.2 Structure des fichiers

```
haccp_report/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── haccp_report.py          # Modèle persistant haccp.report
│   └── report_renderer.py       # AbstractModel + _get_report_values()
├── report/
│   ├── report_action.xml        # ir.actions.report (qweb-pdf)
│   └── report_template.xml      # Template QWeb 6 sections
├── views/
│   ├── haccp_report_views.xml   # List view + Form view haccp.report
│   ├── menu.xml                 # Menu Qualité > Rapports > Rapport HACCP DDPP
│   └── quality_inherit.xml      # Héritage quality.check list → bouton control panel
└── security/
    └── ir.model.access.csv      # Accès lecture/écriture haccp.report
```

---

## 3. Modèle de données

### 3.1 `haccp.report` (modèle persistant)

```python
_name = 'haccp.report'
_description = 'Rapport HACCP DDPP'
_order = 'date_start desc'
```

| Champ | Type | Attributs | Description |
|-------|------|-----------|-------------|
| `name` | Char | computed, store=True | « Rapport HACCP – Mai 2026 » |
| `date_start` | Date | required | Début de la période de surveillance |
| `date_end` | Date | required | Fin de la période de surveillance |
| `responsible_id` | Many2one `res.users` | required, default=uid | Responsable qualité signataire |
| `company_id` | Many2one `res.company` | required, default=company | Société (nom, adresse, logo) |
| `state` | Selection | default='draft' | `draft` / `generated` |
| `check_count` | Integer | computed | Nb de `quality.check` sur la période |
| `alert_count` | Integer | computed | Nb de `quality.alert` sur la période |

Le PDF généré est auto-attaché au record via `attachment_use=True` sur l'`ir.actions.report`.

`name` est calculé automatiquement : `"Rapport HACCP DDPP – {date_start} → {date_end}"`.

### 3.2 `report.haccp_report.report_haccp_ddpp` (AbstractModel — renderer)

Convention Odoo : `_name = 'report.<module>.<template_id>'` — le template_id doit correspondre
à la partie droite du champ `file` dans l'`ir.actions.report` (`haccp_report.report_haccp_ddpp`).

```python
_name = 'report.haccp_report.report_haccp_ddpp'
# models.AbstractModel pur — pas d'héritage de 'report.abstract'
```

Méthode `_get_report_values(docids, data=None)` — retourne :

```python
{
    'docs':            haccp.report records (browsed),
    'points':          quality.point — tous CCP actifs (filtrés HACCP),
    'checks_by_point': {point.id: [quality.check, ...]},  # triés par date asc
    'stats': [
        {
            'point':      quality.point record,
            'count':      int,        # nb total de mesures
            'pass_count': int,        # nb mesures conformes
            'rate':       float,      # taux conformité (0.0–100.0)
            'val_min':    float,
            'val_max':    float,
            'val_avg':    float,
            'alert_count': int,
        },
        ...
    ],
    'alerts':          quality.alert records — filtrés par date, triés par date asc,
    'company':         res.company record,
    'total_checks':    int,           # somme toutes zones
    'total_alerts':    int,
    'global_rate':     float,         # taux conformité global
}
```

**Filtrage :**
- `quality.check` : `create_date >= date_start` AND `create_date <= date_end + 23:59:59`
- `quality.alert` : `create_date >= date_start` AND `create_date <= date_end + 23:59:59`
- `quality.point` : tous les points actifs liés aux checks présents dans la période

---

## 4. Rapport QWeb

### 4.1 Déclaration `ir.actions.report`

```xml
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
```

### 4.2 Structure du template (`report_template.xml`)

Le template hérite de `web.external_layout` (logo société, adresse, pied de page Odoo standard).

**Section 0 — Plan HACCP (introduction)**
Source : `points` (quality.point)
Tableau : Équipement/Zone | Paramètre surveillé | Limite critique | Fréquence | Action corrective prévue
Fréquence : calculée dynamiquement depuis les checks (intervalle moyen entre mesures sur la période) ou affichée comme « 10 min (continu) » si l'écart médian est < 15 min.
Note de bas de tableau : référence à l'arrêté du 21/12/2009 et au Règlement CE 852/2004

**Section 1 — En-tête établissement**
Source : `company`, `docs[0]` (haccp.report)
Contenu : nom société, adresse complète, SIRET, période (date_start → date_end), date d'édition, responsable qualité

**Section 2 — Tableau de synthèse**
Source : `stats`
Tableau : Équipement | Nb mesures | Seuil | T°/HR min | T°/HR max | T°/HR moyenne | Taux conformité | Nb alertes
Ligne TOTAL en bas (total_checks, global_rate, total_alerts)
Couleur : taux < 95% → rouge, 95–99% → orange, ≥ 99% → vert

**Section 3 — Relevés détaillés**
Source : `checks_by_point`
Une sous-section par CCP (saut de page si nécessaire)
Tableau chronologique : Date/Heure | Valeur mesurée | Seuil | Statut (✓ vert / ✗ rouge)
Lignes hors-seuil surlignées en rouge pâle

**Section 4 — Non-conformités et actions correctives**
Source : `alerts`
Rendu conditionnel : `t-if="alerts"` — si aucune alerte, afficher « Aucune non-conformité sur la période »
Pour chaque alerte : référence | équipement | date/heure | valeur mesurée | seuil | durée dépassement | action corrective | responsable | date clôture | statut (Ouverte / Clôturée)

**Section 5 — Signature et mentions légales**
Contenu : zone de signature (responsable qualité + date), mention légale archivage 3 ans (Art. 5 Règl. CE 852/2004), numéro de page (Page X/N), ligne "Généré par Odoo 19 — AIFluence Digital"

### 4.3 CSS

CSS inline dans le template (compatible WeasyPrint — pas de Flexbox, pas de CSS Grid).
Palette de couleurs : bleu institutionnel `#1a5276` pour les en-têtes, rouge `#c0392b` pour les dépassements, vert `#1a7a1a` pour la conformité.

---

## 5. Interface utilisateur

### 5.1 Menu

```
Qualité
└── Rapports
    └── Rapports HACCP DDPP   ← ouvre la list view de haccp.report
```

### 5.2 Form view `haccp.report`

**Header :**
- Bouton principal `🖨️ Générer le PDF` (méthode `action_print_report`) — visible en état `draft` ET `generated`
- Statusbar : `Brouillon` → `Généré`

**Stat buttons (button_box) :**
- `check_count` mesures → ouvre quality.check filtrées par date
- `alert_count` alertes (rouge si > 0) → ouvre quality.alert filtrées par date
- Taux conformité global (vert/orange/rouge selon seuil)
- Icône 📎 PDF → ouvre la pièce jointe si `state == 'generated'`

**Corps du formulaire :**
- Groupe gauche : Date de début, Date de fin
- Groupe droit : Responsable qualité, Société
- Chatter activé (traçabilité : qui a généré quoi et quand)

### 5.3 List view `haccp.report`

Colonnes : Nom | Date début | Date fin | Responsable | Nb mesures | Nb alertes | Conformité | État
Tri par défaut : date_start desc (rapports les plus récents en premier)

### 5.4 Bouton dans `quality.check` list view

Héritage XPath de `quality_control.quality_check_list_view`.
Bouton `📊 Rapport HACCP DDPP` ajouté dans le control panel.
Clic → ouvre un nouveau formulaire `haccp.report` pré-rempli :
- `date_start` = premier jour du mois courant
- `date_end` = date du jour
- `responsible_id` = utilisateur connecté

---

## 6. Sécurité

| Modèle | Groupe | Droits |
|--------|--------|--------|
| `haccp.report` | `quality.group_quality_user` | lecture, écriture, création |
| `haccp.report` | `quality.group_quality_manager` | lecture, écriture, création, suppression |

---

## 7. Points techniques à valider lors du développement

1. **Champ `create_date` vs champ dédié** sur `quality.check` : vérifier si Odoo stocke la date de mesure IoT dans `create_date` ou dans un champ `date` dédié (à inspecter sur `odoo19e_dev`).
2. **Champ `measure`** sur `quality.check` : confirmer le nom exact du champ valeur mesurée (peut être `measure_by` ou `qty_line` selon la version).
3. **Action corrective** sur `quality.alert` : vérifier si le modèle v19 a un champ `activity_ids` ou un champ texte dédié pour les actions correctives.
4. **`attachment_use=True`** : si le PDF est déjà généré pour un record, Odoo le sert depuis le cache. Prévoir un bouton "Regénérer" qui force `attachment_use=False` sur cet appel.
5. **Colonne Fréquence (Section 0)** : `quality.point` n'a pas de champ fréquence natif. Calcul dynamique depuis l'intervalle médian entre checks — si < 15 min afficher « 10 min (continu) ». À implémenter dans `_get_report_values()`.

---

## 8. Ce qui est hors périmètre

- Envoi email automatique du rapport
- Planification automatique (rapport mensuel auto-généré)
- Signature électronique
- Export Excel/CSV
- Dashboard graphique des températures (prévu dans le module `haccp_iot` production)

---

## 9. Références

| Élément | Valeur |
|---------|--------|
| Instance de développement | `http://192.168.1.182:8029` (odoo19e_dev) |
| Module qualité existant | `quality_control` (installé 2026-05-19) |
| QCPs HACCP configurés | Frigo positif (≤4°C), Congélateur (≤-15°C), Stockage sec (≤75% HR) |
| Réglementation | Règlement CE 852/2004, Arrêté 21/12/2009 |
| Guide technique Odoo reports | `AIFD-DEV-RPT-001_Rapports-XML-PDF-Odoo-V19_FR.docx` |
