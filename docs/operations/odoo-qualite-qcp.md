# Odoo Qualité — Configuration QCPs HACCP + Test API

## 1. Activer le mode développeur
Settings → Activate developer mode (lien en bas de la page Settings)

## 2. Créer les 3 Quality Control Points (QCPs)

Quality → Configuration → Control Points → New

### QCP Frigo Positif
- Name : **Frigo Positif — Surveillance HACCP**
- Control Type : **Measure**
- Norm : 2 (température cible en °C)
- Tolerance Min : -30
- Tolerance Max : 4 (seuil critique HACCP)
- Unit of Measure : °C

### QCP Congélateur
- Name : **Congélateur — Surveillance HACCP**
- Control Type : **Measure**
- Norm : -18
- Tolerance Min : -40
- Tolerance Max : -15
- Unit of Measure : °C

### QCP Stockage Sec Humidité
- Name : **Stockage Sec — Humidité HACCP**
- Control Type : **Measure**
- Norm : 55
- Tolerance Min : 0
- Tolerance Max : 75
- Unit of Measure : %

## 3. Récupérer les IDs des QCPs

En mode développeur, l'ID est visible dans l'URL quand vous ouvrez un QCP :
`/web#id=X&model=quality.point`

| QCP | ID Odoo | À noter pour vNode |
|-----|---------|-------------------|
| Frigo Positif | ... | QCP_ID_FRIGO_POSITIF |
| Congélateur | ... | QCP_ID_CONGELATEUR |
| Stockage Sec | ... | QCP_ID_STOCKAGE_SEC |

Ces IDs sont utilisés dans la configuration vNode (voir vnode-config.md).

## 4. Tester la création manuelle
Quality → Quality Checks → New :
- Control Point : Frigo Positif — Surveillance HACCP
- Measure : 3.5 → Status : **Pass** (3.5 ≤ 4°C) ✓

Créer un second check :
- Measure : 6.2 → Status : **Fail** (6.2 > 4°C) ✓

## 5. Exécuter le script de test API

```bash
python3 scripts/test-odoo-api.py \
  --url http://<ip_vps>:8069 \
  --db odoo \
  --user admin \
  --key <odoo_api_key>
```

Expected :
```
[1] Connexion http://<ip_vps>:8069 — DB: odoo
    OK — UID: 2
[2] Lecture des QCPs disponibles
    QCP #1: Frigo Positif — Surveillance HACCP
    QCP #2: Congélateur — Surveillance HACCP
    QCP #3: Stockage Sec — Humidité HACCP
[3] Création quality.check test (5.8°C, QCP #1)
    OK — quality.check ID: 3
[4] Création quality.alert test
    OK — quality.alert ID: 1
[5] Vérification quality.check
    measure=5.8 state=fail
OK — API Odoo Qualité fonctionnelle
```

## 6. Créer l'utilisateur responsable restaurant
Settings → Users → New :
- Name : Responsable Cuisine
- Email : responsable@restaurant.fr
- Application accesses : Quality → Administrateur
