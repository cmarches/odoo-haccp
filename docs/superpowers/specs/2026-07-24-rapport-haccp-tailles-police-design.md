# Spec — Agrandissement des tailles de police du Rapport HACCP DDPP

**Date :** 2026-07-24
**Statut :** Approuvé
**Auteur :** Brainstorming AIFluence Digital
**Périmètre :** `odoo-addons/haccp_report/report/report_template.xml` — lisibilité à l'impression papier

## Contexte

Le rapport HACCP DDPP (PDF généré via QWeb) est lisible à l'écran mais les polices sont trop petites à l'impression papier (8px à 11px selon les éléments). Demande utilisateur : agrandir significativement, en acceptant que le rapport puisse gagner 1-2 pages selon le volume de données — la lisibilité prime sur la compacité.

## Décision

Augmentation d'environ +37% sur toutes les tailles de police du template, avec une table de conversion cohérente qui préserve la hiérarchie visuelle actuelle (titres toujours plus grands que le corps de texte, mentions légales toujours les plus petites) :

| Usage | Actuel | Nouveau |
|---|---|---|
| Mentions légales / bas de page | 8px, 8.5px | 11px, 12px |
| Texte secondaire (labels, dates, tableau signature) | 9px | 12px |
| Corps des tableaux (mesures, relevés) | 9.5px | 13px |
| Titres de section | 10px | 14px |
| Titre principal + bandeau de dates | 11px | 15px |

## Occurrences à modifier (toutes dans `report_template.xml`)

| Ligne | Élément | Actuel | Nouveau |
|---|---|---|---|
| 8 | `.page` (police de base) | 11px | 15px |
| 12 | `.haccp-section-title` | 10px | 14px |
| 18 | `.haccp-table` | 9.5px | 13px |
| 33 | `.legal-note` | 8px | 11px |
| 34 | `.alert-table` | 9px | 12px |
| 45 | Titre "Rapport de surveillance HACCP" (inline) | 11px | 15px |
| 48 | "Responsable qualité :" (inline) | 9px | 12px |
| 53 | Bandeau de dates (inline) | 11px | 15px |
| 56 | "Édité le ..." (inline) | 9px | 12px |
| 97 | Colonne "Action corrective prévue" (inline) | 8.5px | 12px |
| 226 | Encadré "Aucune non-conformité" (inline) | 10px | 14px |
| 281 | "Responsable :" pied de tableau alerte (inline) | 8.5px | 12px |
| 293 | Tableau signature (inline) | 9px | 12px |

## Hors périmètre

- Pas de changement de mise en page (marges, largeurs de colonnes, `page-break`) — uniquement les tailles de police. Si le texte déborde après agrandissement, ce sera visible lors de la vérification PDF réelle et traité séparément si besoin.
- Pas de changement au paperformat (`base.paperformat_euro`, dans `report_action.xml`) — non demandé.

## Vérification

Génération réelle du PDF (via `scripts/deploy-haccp-report.sh` puis impression/export d'un rapport HACCP existant) pour confirmer visuellement le rendu et l'absence de débordement de texte dans les tableaux à largeurs fixes (`table-layout:fixed`).
