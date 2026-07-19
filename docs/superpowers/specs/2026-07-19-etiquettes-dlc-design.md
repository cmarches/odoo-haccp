# Spec — Étiquettes DLC secondaire (portail cuisine + impression Zebra)

**Date :** 2026-07-19
**Statut :** Design validé — prêt pour plan d'implémentation
**Auteur :** Brainstorming AIFluence Digital
**Périmètre :** Impression d'étiquettes DLC secondaire par le personnel de cuisine, via le portail Odoo, sur imprimante thermique réseau

---

## 1. Contexte

Le module `haccp_report` propose déjà un calculateur DLC/DLUO (`haccp.dlc`, wizard `TransientModel`), accessible uniquement depuis le backend Odoo aux utilisateurs internes du groupe `quality.group_quality_user`. Ce calculateur donne une date limite mais ne produit ni impression ni trace persistante.

Le besoin exprimé : le cuisinier doit pouvoir **imprimer physiquement** une étiquette DLC à coller sur un produit ouvert/entamé en cuisine (DLC secondaire — ex. bidon de sauce ouvert, plat préparé la veille), sans que cela nécessite un compte utilisateur interne Odoo (facturé à la licence en Enterprise). Le portail Odoo (utilisateurs portail, gratuits et illimités) est retenu comme point d'entrée.

Une note technique antérieure (`docs/Informations & Discussions/AIFD-HACCP-DLC-V19-Notes-techniques.docx`, mai 2025) avait déjà identifié cette limite native d'Odoo et exploré trois options d'impression Zebra : module tiers payant (VentorTech), WebUSB, ou envoi ZPL brut en réseau (port 9100). C'est cette dernière option qui est retenue ici.

**Matériel confirmé :** imprimante thermique OXHOO TLP200 (compatible ZPL, protocole natif Zebra), connectée en Ethernet/Wi-Fi avec IP fixe sur le réseau cuisine.

---

## 2. Périmètre

- DLC **secondaire uniquement** (produit ouvert/entamé en cuisine). La DLC primaire (produit tel que reçu, gérée nativement par le suivi de lot Odoo) est hors périmètre.
- Un seul établissement (POC actuel) — le design reste générique pour être répliqué tel quel sur chaque instance client (modèle MSP AIFluence Digital, cf. [[project-haccp-architecture-tiers]] dans la mémoire projet), mais aucune fonctionnalité multi-site n'est développée ici.
- Le wizard `haccp.dlc` existant n'est pas modifié — il reste l'outil de calcul rapide côté backend. Le nouveau flux est un module fonctionnel complémentaire, pas un remplacement.

---

## 3. Architecture / flux général

```
[Cuisinier — compte portail individuel, groupe group_haccp_kitchen]
        |
        v
[Portail Odoo — GET/POST /haccp/etiquette/nouvelle]
   - choix produit (liste catégorie "Alimentaire" + saisie libre "Autre")
   - famille + condition (réutilise _DLC_TABLE de haccp.dlc)
   - date d'ouverture (défaut aujourd'hui)
        |
        v (contrôleur Odoo, sudo() après vérification du groupe)
[Modèle persistant haccp.dlc.ouverture]
   - crée l'enregistrement — operateur_id forcé serveur (jamais depuis l'input)
   - calcule duree_jours / date_limite / statut
        |
        v
[Génération ZPL — texte + code-barres Code128 (référence) + QR (URL portail + token)]
        |
        v (socket TCP, port 9100, timeout 3s)
[OXHOO TLP200 — IP fixe réseau cuisine]
        |
        v
[Étiquette imprimée, collée sur le produit]

[Plus tard — scan du QR]
        |
        v
[GET /haccp/etiquette/<id>/<token> — auth='public' pour la lecture]
   - affiche statut (valide/bientôt expiré/expiré)
   - bouton "Marquer terminé/jeté" — visible et actif seulement si connecté
     en tant que membre de group_haccp_kitchen
```

Principe central : le contrôleur porte toute la logique sensible (création d'enregistrement, envoi réseau à l'imprimante) via `sudo()`. Le portail n'a **aucun droit ACL direct** sur le modèle — donc aucune licence utilisateur interne n'est nécessaire, quel que soit le nombre de cuisiniers.

---

## 4. Modèle de données

Nouveau modèle `haccp.dlc.ouverture` dans `odoo-addons/haccp_report/models/`, héritant de `portal.mixin` (token d'accès public standard Odoo) et `mail.thread` (historique horodaté des changements de statut).

| Champ | Type | Détail |
|---|---|---|
| `reference` | Char | Auto-généré via séquence, format `AAAA-JJJ-NNN` (ex : `2026-200-014`) |
| `product_id` | Many2one `product.template` | Optionnel — rempli si choisi dans la liste suggérée |
| `product_name` | Char, requis | Libellé imprimé sur l'étiquette — pré-rempli depuis `product_id` si choisi, sinon saisie libre |
| `famille` | Selection | Même liste que `haccp.dlc` : viande_crue / poisson / charcuterie / laitier / plat_cuisine / legumes / autre |
| `condition` | Selection | refrigere / congele / ambiant |
| `date_ouverture` | Datetime, requis | Défaut = maintenant |
| `operateur_id` | Many2one `res.users`, readonly | Forcé serveur depuis `request.env.user` à la création |
| `duree_jours` | Integer, compute stored | Calculé depuis `_DLC_TABLE` (famille, condition) |
| `date_limite` | Date, compute stored | `date_ouverture + duree_jours` |
| `statut` | Selection, compute stored | `ouvert` / `expire` (recalculé), `termine`, `jete` (positionnés manuellement) |
| `date_cloture` | Datetime | Rempli quand `statut` passe à `termine` ou `jete` |

`_DLC_TABLE` est déplacée dans un module partagé (ex. `models/haccp_dlc_table.py`) importé à la fois par le wizard `haccp.dlc` existant et par `haccp.dlc.ouverture`, pour ne pas dupliquer la table de durées.

---

## 5. Interface portail

Contrôleur dédié `controllers/haccp_portal.py`.

### a) `GET`/`POST /haccp/etiquette/nouvelle` — `auth='user'`

- Accès restreint aux utilisateurs membres du nouveau groupe `group_haccp_kitchen` (hérite de `base.group_portal`) — vérifié en tête de contrôleur, sinon 403.
- Formulaire : produit (liste déroulante des produits de la catégorie "Alimentaire" + option "Autre : saisie libre"), famille, condition, date d'ouverture (pré-remplie, modifiable).
- Aperçu de la DLC calculée avant validation (même logique que le wizard actuel, exposée en JS ou en re-render serveur).
- Soumission : crée l'enregistrement, génère le ZPL, l'envoie à l'imprimante, affiche une page de confirmation :
  - Succès : "✓ Étiquette envoyée à l'imprimante cuisine"
  - Échec réseau/imprimante : message d'erreur + bouton "Réessayer l'impression" (renvoie uniquement le ZPL de l'enregistrement déjà créé — pas de doublon)

### b) `GET /haccp/etiquette/<id>/<access_token>` — `auth='public'`

- Cible du QR code de l'étiquette imprimée.
- Lecture toujours publique (comme un partage de document Odoo standard) : produit, référence, date d'ouverture, opérateur, DLC, statut (avec code couleur vert/orange/rouge).
- Bouton "Marquer terminé/jeté" visible seulement si l'utilisateur courant est connecté et membre de `group_haccp_kitchen`. Sinon, invite à se connecter ; l'action reste inaccessible tant que non connecté.
- Token invalide ou enregistrement inexistant → 404.

---

## 6. Génération et envoi du ZPL

Template ZPL (chaîne Python avec placeholders), généré côté serveur à partir de l'enregistrement :

```
^XA
^CF0,30
^FO20,20^FD{product_name}^FS
^CF0,20
^FO20,60^FDOuvert: {date_ouverture}  Par: {operateur_name}^FS
^FO20,90^GB300,40,2^FS
^CF0,28
^FO30,100^FDDLC: {date_limite} (J+{duree_jours})^FS
^FO20,150^FDConservation: {condition_label}^FS
^BY2^FO20,180^BCN,50,Y,N,N^FD{reference}^FS
^FO250,150^BQN,2,4^FDQA,{portal_url}/haccp/etiquette/{id}/{access_token}^FS
^XZ
```

- Envoi via socket TCP brut vers `printer_ip:9100`, timeout 3s.
- Adresse IP de l'imprimante en paramètre système (`ir.config_parameter`, clé `haccp_report.zebra_printer_ip`), configurable en Paramètres généraux — pas de valeur en dur dans le code.
- En cas d'échec d'envoi, l'enregistrement `haccp.dlc.ouverture` est conservé (la traçabilité HACCP ne dépend pas du succès de l'impression physique) ; seul l'écran de confirmation reflète l'échec.

---

## 7. Sécurité et accès

- Nouveau groupe `group_haccp_kitchen` (hérite de `base.group_portal`), assigné individuellement à chaque compte portail de cuisinier.
- `ir.model.access.csv` : **aucun droit direct** sur `haccp.dlc.ouverture` pour ce groupe. Toutes les opérations passent par le contrôleur en `sudo()`, après vérification explicite de `request.env.user.has_group('haccp_report.group_haccp_kitchen')`.
- Champs modifiables par le formulaire portail strictement whitelistés côté contrôleur (produit, famille, condition, date d'ouverture). `operateur_id` est toujours affecté depuis `request.env.user`, jamais depuis l'input du formulaire — empêche un cuisinier d'attribuer une ouverture à un collègue.
- La page de consultation publique (`auth='public'`) n'expose que les champs de l'étiquette elle-même — aucune fuite d'autres données HACCP ou d'inventaire.
- Ce groupe et ce contrôleur sont génériques et réutilisables sans modification pour chaque nouvelle instance cliente (1 instance Odoo par client, cf. [[project-haccp-architecture-tiers]]).

---

## 8. Tests

- Unitaires : calcul DLC (réutilise/étend les tests existants de `haccp.dlc`), génération de la référence, transitions de statut (`ouvert` → `termine`/`jete`, `ouvert` → `expire` si `date_limite` dépassée).
- Unitaires : contenu du template ZPL généré (pas d'envoi réseau réel — socket mocké).
- Contrôleur : accès refusé sans groupe `group_haccp_kitchen` (403), `operateur_id` toujours forcé serveur même si l'input le contient, token invalide → 404, lecture publique sans connexion, action de clôture refusée si non connecté.
- Pas de test d'intégration imprimante réelle en CI (même approche que pour l'intégration TTN, cf. [[project-demo-simulate-sensor]]) — vérification manuelle documentée une fois le matériel OXHOO TLP200 disponible sur site.

---

## 9. Hors périmètre (explicitement exclu de cette itération)

- DLC primaire / ré-étiquetage de lots reçus fournisseur.
- Lien avec `stock.lot` — le numéro de référence de `haccp.dlc.ouverture` est indépendant du suivi de lot Odoo.
- Multi-site / multi-restaurant dans une même instance.
- Rapport de gaspillage (statistiques sur les étiquettes `jete`) — les données sont capturées (`statut`, `date_cloture`) mais aucun rapport n'est construit dessus pour l'instant.
- Fallback USB/pilote local si l'imprimante réseau est indisponible.
