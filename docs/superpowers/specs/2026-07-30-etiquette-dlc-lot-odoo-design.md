# Spec — Lien Étiquette DLC ↔ Lot Odoo (stock.lot)

**Date :** 2026-07-30
**Statut :** Design validé — prêt pour plan d'implémentation
**Auteur :** Brainstorming AIFluence Digital
**Périmètre :** Lier le flux d'impression d'étiquette DLC secondaire (existant, cf. `docs/superpowers/specs/2026-07-19-etiquettes-dlc-design.md`) au suivi de lot natif Odoo (`stock.lot`)

---

## 1. Contexte

La fonctionnalité "Étiquettes DLC" (mergée le 2026-07-20, commit `4a97030`) génère aujourd'hui une référence purement interne au module HACCP (`haccp.dlc.ouverture.reference`, séquence `AAAA-JJJ-NNN`), totalement indépendante du système de traçabilité lot/série natif d'Odoo (`stock.lot`). Ce découplage était documenté comme hors périmètre explicite de la v1 (section 9 de la spec initiale).

Vérification factuelle sur l'instance de démo (2026-07-30, avant ce design) :
- Un seul produit existe au catalogue ("Sauce tomate maison"), `tracking='none'`.
- 0 `stock.lot` dans la base.
- Modules `product_expiry` et `mrp` : non installés.

Le besoin exprimé recouvre trois motivations combinées : traçabilité/rappel produit, éviter la double saisie (le lot existe déjà côté réception fournisseur), et pouvoir croiser les DLC secondaires avec les mouvements de stock standard Odoo (reporting/valorisation).

Une extension plus large vers une gestion complète des approvisionnements (modules **MRP**/**MPS**) a été évoquée en cours de brainstorm, mais explicitement écartée de cette itération (cf. section 9 — Hors périmètre) : elle suppose des nomenclatures par plat et des ordres de fabrication, un changement d'échelle disproportionné par rapport au besoin actuel (lier un code-barre à un lot).

---

## 2. Périmètre

- Lier chaque `haccp.dlc.ouverture` à un `stock.lot` Odoo, réel (produit reçu, lot existant) ou créé à la volée (plat cuisiné sans lot entrant).
- Afficher, optionnellement, la DLC primaire native Odoo (`product_expiry`) en complément de la DLC secondaire, avec plafonnement de sécurité.
- Retirer le code-barre Code128 de l'étiquette imprimée (aucun lecteur ne l'exploite aujourd'hui) au profit d'un affichage texte simple.
- **Hors périmètre** (voir section 9) : MRP/MPS, code-barre pour le lot, traçabilité composants → plat cuisiné, scan physique du lot fournisseur.

---

## 3. Modèle de données

Ajout sur `haccp.dlc.ouverture` (`odoo-addons/haccp_report/models/haccp_dlc_ouverture.py`) :

```python
lot_id = fields.Many2one('stock.lot', string='Lot Odoo', copy=False, readonly=True)
```

- `readonly=True` : jamais saisi/modifié à la main, déterminé uniquement par la logique serveur au moment de la soumission — même principe que `reference`.
- `reference` (séquence `AAAA-JJJ-NNN`) est **conservée** comme identifiant interne de l'enregistrement (titre, recherche, historique) ; elle continue d'exister indépendamment du lot.
- Aucune migration : les enregistrements historiques (créés avant cette fonctionnalité) gardent `lot_id` vide — état normal, pas une anomalie.
- Aucun champ inverse ajouté sur `stock.lot` en v1 (pas de smart button dédié) — hors périmètre, la consultation croisée peut se faire par recherche filtrée standard.

---

## 4. Configuration

Le menu "Méthode HACCP" (`menu_haccp_reports_root`, `odoo-addons/haccp_report/views/menu.xml`) n'a aujourd'hui aucune entrée Configuration. Ajout :

- Nouveau menu **Configuration**, dernier de la liste sous `menu_haccp_reports_root`, restreint à un groupe manager (groupe exact à confirmer en phase de plan — vérifier l'existence de `quality.group_quality_manager` ou équivalent).
- Écran standard Odoo : extension de `res.config.settings` avec un champ booléen :

  ```python
  haccp_use_native_expiry = fields.Boolean(
      string="Utiliser la DLC native Odoo (product_expiry)",
      config_parameter='haccp_report.use_native_expiry',
  )
  ```

  Stocké via le mécanisme standard `config_parameter` (`ir.config_parameter`) — pas de nouvelle table.

- **Comportement :**
  - Décoché (défaut) : comportement actuel, aucune vérification ni affichage de DLC primaire.
  - Coché : active l'affichage de `lot_id.expiration_date` et le plafonnement décrit en section 6.
  - Si `product_expiry` n'est pas installé, la case reste visible avec un message d'avertissement ("module non installé") — pas de crash.
  - Réglage **global** (on/off pour toute l'instance), mais son effet reste **best-effort par enregistrement** : si un lot précis n'a pas de `expiration_date` renseignée, on l'ignore silencieusement pour celui-là (pas de blocage, pas d'erreur).

---

## 5. Logique du flux de soumission (`haccp_etiquette_submit`)

Modification du contrôleur `odoo-addons/haccp_report/controllers/haccp_portal.py`, avant la création de l'enregistrement :

1. **Résolution produit** : si `product_id` vide (saisie libre, produit non catalogué) → blocage. Message orienté vers l'action correctrice côté responsable, pas côté cuisinier : *"Produit non reconnu — demandez à votre responsable de l'ajouter au catalogue avec suivi par lot activé."* (rendu via le même mécanisme d'erreur que les blocages existants du formulaire).

2. **Vérification du tracking** : si `product_id.tracking == 'none'` → blocage, message analogue : *"Suivi par lot non activé sur ce produit — demandez à votre responsable de l'activer."*

3. **Résolution du lot** (tracking actif — `lot` ou `serial`) :
   - Recherche des `stock.lot` existants pour le produit avec quantité disponible (`stock.quant` qty > 0) à ce moment :
     - **0 résultat** → création automatique d'un nouveau `stock.lot` dont le **nom reprend directement la valeur de `reference`** de l'enregistrement (pas de séquence séparée — évite toute divergence entre l'identifiant interne et le nom du lot pour les lots auto-créés). Couvre le cas "plat cuisiné" (pas de lot entrant fournisseur) aussi bien que le cas exceptionnel d'un produit tracké sans lot en stock.
     - **1 résultat** → sélection automatique, invisible pour l'utilisateur (cas courant : un seul bocal en stock).
     - **Plusieurs résultats** → seul cas où le formulaire affiche un sélecteur de lot avant impression (ambiguïté réelle à trancher par l'utilisateur).
   - Limitation documentée : produits multi-variantes (`product.template` avec plusieurs `product.product`) non gérés finement en v1 — cas rare pour un catalogue alimentaire de restaurant.

4. **Vérification DLC primaire** (si `haccp_report.use_native_expiry` activé ET `product_expiry` installé) :
   - Si `lot_id.expiration_date` est renseignée et que la `date_limite` calculée (DLC secondaire) la dépasse → plafonner `date_limite` à `expiration_date`. Les deux dates sont conservées pour affichage (DLC produit d'origine + DLC secondaire).
   - Si `expiration_date` absente → ignorer silencieusement, comportement inchangé.

5. Création de `haccp.dlc.ouverture` avec `lot_id` renseigné (`reference` continue d'être générée comme avant), puis impression.

---

## 6. Génération ZPL (modification)

`odoo-addons/haccp_report/models/zpl_printer.py::build_zpl()` — retrait de la ligne code-barre Code128 (`^BCN`), qui n'est lue par aucun processus du système (la clôture d'étiquette se fait par scan du QR, pas par recherche via code-barre). C'est aussi la ligne à l'origine du bug de chevauchement corrigé lors du test matériel initial (commit `a398379`).

Remplacement par des lignes texte simples :
- `reference` (déjà présente ailleurs sur l'étiquette ou ajoutée en clair)
- Numéro de lot (`lot_id.name`)
- Si activé et disponible : DLC produit d'origine (`lot_id.expiration_date`)

Le QR (`^BQN`, URL portail + token) est conservé à l'identique — c'est le seul élément réellement scanné dans le flux existant (accès à la fiche/clôture).

Pas de code-barre pour le numéro de lot non plus (voir section 9 — raisons détaillées).

---

## 7. Cas limites et gestion des erreurs

- **Produit multi-variantes** : limitation documentée (section 5), pas de traitement spécifique en v1.
- **Création concurrente** : deux impressions simultanées pour un produit sans lot existant pourraient créer deux `stock.lot` distincts au lieu d'un seul. Risque accepté tel quel (volume réel : une cuisine, pas un flux à haut débit) — pas de verrou applicatif ajouté.
- **Clôture d'étiquette** ("terminé"/"jeté") : n'impacte pas le `stock.lot` — pas de décrémentation de stock ni de changement d'état du lot. Le lot reste un repère de traçabilité pur tant que le futur module stock/appros n'est pas construit.
- **`product_expiry` non installé alors que la case Configuration est cochée** : dégradation silencieuse (comme si la case était décochée), avec le message d'avertissement de la section 4.

---

## 8. Tests

Complète la suite existante (`./scripts/deploy-haccp-report.sh --test`) :

- Résolution du lot : 0 / 1 / plusieurs lots existants avec quantité disponible → bon branchement, y compris création automatique.
- Blocages : produit hors catalogue (`product_id` vide), tracking désactivé — messages corrects.
- Plafonnement DLC primaire : avec/sans `product_expiry` installé, avec/sans `haccp_report.use_native_expiry` activé, avec/sans `expiration_date` renseignée sur le lot.
- Contenu ZPL généré : absence de la commande code-barre, présence des lignes texte référence + lot (+ DLC produit d'origine si applicable).
- Écran Configuration : lecture/écriture du paramètre, affichage de l'avertissement si `product_expiry` absent.

Pas de test d'intégration imprimante réelle en CI (même approche que le reste du module) — vérification manuelle sur le matériel OXHOO TLP200 avant mise en production chez un client, pour confirmer l'absence de régression de mise en page suite au retrait du code-barre.

---

## 9. Hors périmètre (explicitement exclu de cette itération)

- **MRP / MPS** (nomenclatures par plat, ordres de fabrication, planification des approvisionnements) : évoqué en brainstorm comme évolution naturelle si un client demande un jour du coût de revient par recette ou une décrémentation automatique du stock d'ingrédients. Mérite un brainstorm et une spec dédiés le moment venu — ne pas rouvrir cette spec pour l'introduire a posteriori.
- **Traçabilité composants → plat cuisiné** : le lot créé pour un plat cuisiné n'a aucun lien vers les lots des ingrédients qui le composent. Nécessiterait une modélisation proche d'un ordre de fabrication (cf. point précédent).
- **Code-barre pour le numéro de lot** : discuté et écarté. Un code-barre de lot aurait un lecteur natif potentiel (l'app Barcode/Inventory d'Odoo pour les mouvements de stock), contrairement à l'ancien code-barre de référence — mais aucun mouvement de stock réel n'existe aujourd'hui sur ces produits (0 `stock.quant`), et le lot n'a pas la même signification selon qu'il s'agit d'un produit acheté ou d'un plat cuisiné tant que MRP n'est pas en place. À réévaluer **avec** le futur chantier stock/appros/MRP, pas indépendamment.
- **Scan physique du lot fournisseur** : capturer le lot réellement ouvert via une douchette scannant le code-barre de l'emballage, plutôt que de déduire le lot du stock Odoo. Plus rigoureux pour la traçabilité réelle, mais nécessite du matériel et un mapping code-barre fournisseur → lot Odoo qui n'existent pas — évolution V2 envisageable.
- **Écriture dans les champs natifs `product_expiry`** : ce design ne fait que **lire** `expiration_date` pour comparaison/affichage, jamais l'inverse — modifier les champs natifs casserait le calcul automatique natif d'Odoo (basé sur `expiration_time` et la date de réception du lot).
