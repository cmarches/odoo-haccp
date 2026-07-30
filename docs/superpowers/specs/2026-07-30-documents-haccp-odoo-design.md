# Spec — Documents HACCP dans l'app Documents Odoo

**Date :** 2026-07-30
**Statut :** Design validé — prêt pour plan d'implémentation
**Auteur :** Brainstorming AIFluence Digital
**Périmètre :** Centraliser les Rapports HACCP générés, la Bibliothèque de documents existante et de nouveaux justificatifs de formation individuelle dans l'app **Documents** (Odoo Enterprise), avec accès portail pour le gérant et la cuisine.

---

## 1. Contexte

Le module `haccp_report` gère aujourd'hui deux types de documents séparément :
- **Rapports HACCP** (`haccp.report`) : PDF généré à la demande via un rapport QWeb, sauvegardé automatiquement en pièce jointe (`ir.actions.report` avec `attachment` configuré — cf. `report/report_action.xml:10`).
- **Bibliothèque de documents** (`haccp.document`) : PDFs de référence (réglementation, affiches, fiches pratiques, relevés) synchronisés depuis un manifest externe et stockés en pièce jointe (`models/haccp_document.py`).

Aucun des deux n'est accessible depuis un portail — usage interne uniquement (utilisateurs internes, groupe `quality.group_quality_user`/`quality.group_quality_manager`).

**Motivations du changement** (brainstorming du 2026-07-30) :
1. Centraliser l'organisation (dossiers) plutôt que d'avoir des documents dispersés entre plusieurs modèles.
2. Permettre un partage externe simple (auditeur, inspecteur sanitaire) sans compte Odoo.
3. Donner un accès direct depuis le portail existant (gérant, cuisine) sans passer par le backend.

L'app **Documents** (Odoo Enterprise) est maintenant installée sur l'instance de démo. Vérification factuelle faite sur cette instance (192.168.1.182, base `odoo19e_dev`) :
- Module `documents` : installé.
- `documents.document` est un modèle **unifié** : les dossiers sont des `documents.document` avec `type='folder'` ; les fichiers avec `type='binary'` (champ `attachment_id` vers l'`ir.attachment` existant). Champs clés confirmés : `name`, `attachment_id` (→ `ir.attachment`), `folder_id` (→ `documents.document`, auto-référence), `res_model`/`res_id` (lien retour vers l'enregistrement métier d'origine), `partner_id`, `owner_id`, `company_id`, `tag_ids`.
- **`documents.access`** : modèle de droit d'accès par partenaire — `document_id` (→ `documents.document`, requis), `partner_id` (→ `res.partner`, requis), `role` (`view`/`edit`), `expiration_date` (optionnelle). C'est le mécanisme qui donnera l'accès portail au gérant/à la cuisine sur un dossier précis.
- **`documents.sharing`** : génération de lien de partage public — fonctionnalité native de l'UI Documents, aucun développement nécessaire pour le cas "auditeur externe" (le gérant génère le lien lui-même depuis l'interface standard).
- Dossiers racine existants sur l'instance (seedés par d'autres apps) : Inbox, Finance, Legal, Marketing, Admin, Products — rien pour HACCP, à créer.

**Décision explicite** : cette fonctionnalité cible **uniquement les clients Odoo Enterprise**. Les clients Community (Cas A, `haccp_report_ce`) gardent le comportement actuel (pièces jointes classiques) — pas de fallback CE développé pour cette itération.

---

## 2. Périmètre

- Créer la structure de dossiers Documents : **HACCP** (racine) > **Rapports HACCP**, **Bibliothèque de documents**, **Formations individuelles**.
- Lier les enregistrements `haccp.report` et `haccp.document` existants à des `documents.document` (fichiers) dans les dossiers correspondants, sans changer leur mécanisme de génération/synchronisation actuel.
- Nouveau modèle `haccp.formation.certificat` pour les justificatifs de formation individuelle, natif Documents dès le départ.
- Nouveau groupe portail `group_haccp_gerant` (parallèle à `group_haccp_kitchen` existant).
- Accès portail via `documents.access` : gérant → les 3 dossiers ; cuisine → Bibliothèque + Formations individuelles uniquement (pas les Rapports HACCP).
- **Hors périmètre** (cf. section 8) : support Community Edition, suivi de péremption des formations individuelles, workflow de validation/approbation des documents, configuration programmatique du partage externe (`documents.sharing` reste un usage manuel du gérant).

---

## 3. Structure Documents

```
HACCP (documents.document, type=folder, folder_id=False)
├── Rapports HACCP        (type=folder, folder_id=HACCP)   — accès : group_haccp_gerant
├── Bibliothèque de documents (type=folder, folder_id=HACCP) — accès : group_haccp_gerant + group_haccp_kitchen
└── Formations individuelles  (type=folder, folder_id=HACCP) — accès : group_haccp_gerant + group_haccp_kitchen
```

Les 3 dossiers et le dossier racine sont créés via données XML (`ir.model.data` avec `noupdate="1"`, comme les groupes de sécurité existants) — pas de création à la volée par le code.

---

## 4. Accès portail

**Nouveau groupe `group_haccp_gerant`** (`security/haccp_gerant_security.xml`, même structure que `group_haccp_kitchen`) :
```xml
<record id="group_haccp_gerant" model="res.groups">
  <field name="name">HACCP — Gérant (portail)</field>
  <field name="implied_ids" eval="[(4, ref('base.group_portal'))]"/>
</record>
```

**Octroi d'accès** : pour chaque dossier, un `documents.access` par partenaire portail (gérant et/ou cuisine selon le dossier). Puisque l'appartenance aux groupes portail change dynamiquement (ajout/retrait de comptes) et que le volume de comptes portail par instance cliente est faible (architecture 1 instance Odoo par client, quelques comptes gérant/cuisine tout au plus), l'octroi se fait via une **action manuelle unique** "Synchroniser les accès Documents HACCP" (bouton sur les groupes ou action serveur dédiée) : elle parcourt les membres actuels de `group_haccp_gerant`/`group_haccp_kitchen` et crée les `documents.access` manquants sur les dossiers correspondants (idempotent — ne duplique pas un accès déjà existant). Pas de déclenchement automatique à l'ajout d'un utilisateur au groupe (éviterait de surcharger le scope avec un hook sur `res.users`/`res.groups` pour un nombre de comptes de toute façon restreint) — le gérant ou l'intégrateur relance l'action après tout changement de composition des groupes.

Pas de retrait automatique des `documents.access` à la désactivation d'un compte dans cette itération (cf. hors périmètre) — un utilisateur désactivé perd de toute façon l'accès au portail lui-même.

---

## 5. Rattachement des documents existants (Rapports HACCP, Bibliothèque)

**Principe** : ne pas ajouter de nouveau champ sur `haccp.report` ni `haccp.document` — `documents.document` porte déjà `res_model`/`res_id` pointant vers l'enregistrement d'origine, c'est le lien natif Odoo à utiliser. Pour retrouver le `documents.document` d'un enregistrement donné : `env['documents.document'].search([('res_model', '=', 'haccp.report'), ('res_id', '=', report.id)])`.

**Sur `haccp.report`** : à la génération du PDF (le mécanisme `attachment` de `ir.actions.report` existant crée/maj déjà l'`ir.attachment`), une méthode crée ou met à jour le `documents.document` correspondant (`attachment_id` = la pièce jointe du rapport, `folder_id` = dossier "Rapports HACCP", `res_model`/`res_id` = le rapport). Pas de changement au template QWeb ni à la génération PDF elle-même.

**Sur `haccp.document`** : même principe, déclenché dans `action_sync_documents`/`action_load_demo_data` (`models/haccp_document.py`) juste après la création/mise à jour de l'`ir.attachment` existant — `folder_id` = dossier "Bibliothèque de documents".

---

## 6. Nouveau modèle `haccp.formation.certificat`

```python
employe_id = fields.Many2one('res.users', string='Employé', required=True)
type_formation = fields.Selection([
    ('haccp_initiale', 'HACCP initiale'),
    ('recyclage_haccp', 'Recyclage HACCP'),
    ('allergenes', 'Allergènes'),
    ('hygiene_alimentaire', 'Hygiène alimentaire'),
    ('autre', 'Autre'),
], string='Type de formation', required=True)
date_formation = fields.Date(string='Date de formation', required=True)
document_id = fields.Many2one(
    'documents.document', string='Justificatif', required=True
)
commentaire = fields.Text(string='Commentaire')
```

- `employe_id` référence `res.users` (cohérent avec `operateur_id` sur `haccp.dlc.ouverture`) — pas de dépendance au module RH, décision explicite (pas de gestion RH existante dans ce module).
- Pas de suivi de péremption/alerte dans cette itération (décision explicite) — champ `date_formation` simple, sans calcul de validité.
- À la création d'un `haccp.formation.certificat`, le `document_id` choisi (ou uploadé) doit être classé dans le dossier "Formations individuelles" — soit en le créant directement dans ce dossier depuis l'UI Documents (le plus simple), soit en forçant `folder_id` par défaut à la création si l'utilisateur uploade ailleurs.
- Accès : création réservée aux groupes internes (`quality.group_quality_user`/`manager`, comme les autres modèles du module) — la consultation portail passe uniquement par `documents.access` sur le dossier, pas par un accès direct au modèle `haccp.formation.certificat` (même principe que `haccp.dlc.ouverture` : aucun droit ACL portail direct).

---

## 7. Sécurité et accès

- `ir.model.access.csv` : nouvelles lignes pour `haccp.formation.certificat`, groupes `quality.group_quality_user` (lecture/écriture/création) et `quality.group_quality_manager` (+ suppression) — même schéma que `haccp.dlc.ouverture`.
- Aucun droit ACL portail direct sur `haccp.report`, `haccp.document` ou `haccp.formation.certificat` — l'accès portail passe exclusivement par `documents.access` sur les dossiers Documents, jamais par un accès direct aux modèles métier HACCP.
- Le partage externe (auditeur) utilise `documents.sharing`, fonctionnalité standard de l'UI Documents — aucune configuration programmatique, usage manuel du gérant au cas par cas.

---

## 8. Hors périmètre (explicitement exclu de cette itération)

- **Support Community Edition** : l'app Documents est Enterprise-only ; les clients CE gardent le comportement actuel (pièces jointes classiques), pas de fallback développé.
- **Suivi de péremption des formations individuelles** : pas d'alerte de renouvellement dans cette itération — pourrait être ajouté plus tard sur le modèle de la DLC secondaire si le besoin se confirme.
- **Workflow de validation/approbation** des documents (fonctionnalité native de l'app Documents mais non exploitée ici) — les documents sont simplement classés et partagés, pas soumis à un circuit de validation.
- **Configuration programmatique du partage externe** : `documents.sharing` reste un geste manuel du gérant depuis l'UI standard, pas une action automatisée par le module.
- **Retrait automatique des accès** (`documents.access`) à la désactivation d'un compte portail — un compte désactivé perd de toute façon l'accès au portail lui-même, donc pas de nettoyage additionnel jugé nécessaire pour l'instant.
- **Dossiers/accès multi-sites** : l'architecture reste 1 instance Odoo par client (cf. mémoire projet `project-haccp-architecture-tiers`) — pas de séparation de dossiers par site dans une même instance.
