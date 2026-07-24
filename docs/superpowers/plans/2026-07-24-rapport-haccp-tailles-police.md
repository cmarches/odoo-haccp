# Rapport HACCP — Agrandissement des polices Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Augmenter les tailles de police du template QWeb du Rapport HACCP DDPP (`report_template.xml`) d'environ +37%, pour une meilleure lisibilité à l'impression papier, sans changer la mise en page (marges, largeurs de colonnes, sauts de page).

**Architecture:** Modification de valeurs `font-size` CSS/inline dans un seul fichier XML QWeb, selon la table de conversion approuvée dans `docs/superpowers/specs/2026-07-24-rapport-haccp-tailles-police-design.md`. Aucune logique Python ni modèle de données concerné.

**Tech Stack:** Odoo QWeb (XML + CSS inline), module `haccp_report`.

---

## Context an engineer needs before starting

- **Design spec (approuvé) :** `docs/superpowers/specs/2026-07-24-rapport-haccp-tailles-police-design.md` — contient la table de conversion complète avec numéros de ligne.
- **Fichier unique concerné :** `odoo-addons/haccp_report/report/report_template.xml` — 13 occurrences de `font-size` à modifier (dans le bloc `<style>` et en inline).
- **Pas de test automatisé existant** ne référence ces valeurs de police (`grep -rn "font-size" odoo-addons/haccp_report/tests/*.py` ne retourne rien) — la vérification est manuelle (génération PDF réelle), pas TDD.
- **Déploiement/vérification réelle :** `scripts/deploy-haccp-report.sh --update` puis génération d'un rapport HACCP existant en PDF sur le serveur de dev (192.168.1.182:8029) pour inspection visuelle — voir mémoire `project-local-setup` pour la procédure de reprise standard, et `feedback-deploy-restart` (redémarrage du conteneur nécessaire uniquement si des fichiers Python changent — pas le cas ici, XML seul, un simple `--update` suffit).

---

## Task 1: Agrandir toutes les tailles de police du template

**Files:**
- Modify: `odoo-addons/haccp_report/report/report_template.xml`

- [ ] **Step 1: Appliquer les 13 changements de `font-size`**

Dans `odoo-addons/haccp_report/report/report_template.xml`, remplacer chaque valeur selon cette table (correspondance exacte, ligne par ligne au moment de l'édition — les numéros ci-dessous sont ceux de la version actuelle, à ré-identifier si le fichier a changé depuis) :

| Ligne | Contexte | Ancienne valeur | Nouvelle valeur |
|---|---|---|---|
| 8 | `.page` (style de base, dans l'attribut `style` de la div `class="page"`) | `font-size: 11px` | `font-size: 15px` |
| 12 | `.haccp-section-title` (dans le bloc `<style>`) | `font-size: 10px` | `font-size: 14px` |
| 18 | `.haccp-table` (dans le bloc `<style>`) | `font-size: 9.5px` | `font-size: 13px` |
| 33 | `.legal-note` (dans le bloc `<style>`) | `font-size: 8px` | `font-size: 11px` |
| 34 | `.alert-table` (dans le bloc `<style>`) | `font-size: 9px` | `font-size: 12px` |
| 45 | Titre "Rapport de surveillance HACCP" (style inline) | `font-size:11px` | `font-size:15px` |
| 48 | "Responsable qualité :" (style inline) | `font-size:9px` | `font-size:12px` |
| 53 | Bandeau de dates (style inline) | `font-size:11px` | `font-size:15px` |
| 56 | "Édité le ..." (style inline) | `font-size:9px` | `font-size:12px` |
| 97 | Colonne "Action corrective prévue" (style inline sur `<td>`) | `font-size:8.5px` | `font-size:12px` |
| 226 | Encadré "Aucune non-conformité enregistrée" (style inline) | `font-size:10px` | `font-size:14px` |
| 281 | "Responsable :" pied de tableau alerte (style inline sur `<td>`) | `font-size:8.5px` | `font-size:12px` |
| 293 | Tableau signature (style inline) | `font-size:9px` | `font-size:12px` |

Ne rien changer d'autre (couleurs, marges, largeurs de colonnes, sauts de page, structure HTML) — uniquement les valeurs `font-size`.

- [ ] **Step 2: Vérifier qu'aucune occurrence de `font-size` n'a été oubliée**

Run: `grep -n "font-size" odoo-addons/haccp_report/report/report_template.xml`
Expected: 13 lignes, toutes avec l'une des nouvelles valeurs (11px, 12px, 13px, 14px, 15px) — aucune ancienne valeur (8px, 8.5px, 9px, 9.5px, 10px) restante, sauf si une valeur neuve coïncide légitimement avec une ancienne (ce n'est pas le cas ici, la table de conversion ne produit aucune valeur en doublon avec une valeur de départ).

- [ ] **Step 3: Déployer et générer un rapport PDF réel pour vérification visuelle**

Run: `./scripts/deploy-haccp-report.sh --update`
(Pas de redémarrage du conteneur nécessaire — fichier XML seul, pas de modèle Python modifié.)

Puis, dans Odoo (http://192.168.1.182:8029, module HACCP), ouvrir ou créer un Rapport HACCP DDPP existant et générer le PDF via l'action "Imprimer". Vérifier visuellement :
- Le texte est nettement plus lisible qu'avant.
- Aucun texte ne déborde de sa cellule dans les tableaux à largeur fixe (`table-layout:fixed`) — en particulier la colonne "Action corrective prévue" (la plus étroite avec le plus de texte).
- La hiérarchie visuelle est préservée (titres > corps de texte > mentions légales).

Si un débordement de texte est constaté, ce n'est pas bloquant pour ce plan (hors périmètre du spec — ajustement de mise en page à traiter séparément si besoin) mais doit être signalé.

- [ ] **Step 4: Commit**

```bash
git add odoo-addons/haccp_report/report/report_template.xml
git commit -m "feat(haccp): agrandir les tailles de police du rapport HACCP pour l'impression papier"
```
