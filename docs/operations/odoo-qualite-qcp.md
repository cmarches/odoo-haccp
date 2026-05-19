# Odoo Qualité — Configuration QCPs HACCP + API

## Prérequis

- Odoo 19 EE opérationnel sur `http://192.168.1.182:8029` (ubuntuserver24odoo)
- Base de données : `odoo19e_dev`
- Module `quality_control` installé (voir étape 1)

## 1. Installer le module quality_control

Le module n'est pas installé par défaut. Installation via WebUI ou API :

**Via WebUI :** Apps → rechercher "Quality Control" → Install

**Via API (si WebUI bloqué) :**
```python
import xmlrpc.client
url = "http://192.168.1.182:8029"
db = "odoo19e_dev"
uid = 2  # admin
key = "<api_key>"
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

# Trouver l'ID du module
modules = models.execute_kw(db, uid, key, "ir.module.module", "search_read",
    [[["name", "=", "quality_control"]]], {"fields": ["id", "name", "state"]})
# Installer
models.execute_kw(db, uid, key, "ir.module.module", "button_immediate_install",
    [[modules[0]["id"]]])
```

## 2. Créer les 3 Quality Control Points (QCPs)

Quality → Configuration → Control Points → New

### QCP Frigo Positif — ID : **#1**
| Paramètre | Valeur |
|-----------|--------|
| Name | Frigo Positif — Surveillance HACCP |
| Control Type | Measure |
| Norm | 2 (°C cible) |
| Tolerance Min | -30 |
| Tolerance Max | **4** (seuil HACCP critique) |
| Unit of Measure | °C |

### QCP Congélateur — ID : **#2**
| Paramètre | Valeur |
|-----------|--------|
| Name | Congélateur — Surveillance HACCP |
| Control Type | Measure |
| Norm | -18 (°C cible) |
| Tolerance Min | -40 |
| Tolerance Max | **-15** (seuil HACCP critique) |
| Unit of Measure | °C |

### QCP Stockage Sec — ID : **#3**
| Paramètre | Valeur |
|-----------|--------|
| Name | Stockage Sec — Humidité HACCP |
| Control Type | Measure |
| Norm | 55 (% cible) |
| Tolerance Min | 0 |
| Tolerance Max | **75** (seuil HACCP critique) |
| Unit of Measure | % |

## 3. Connexion API XML-RPC

```python
import xmlrpc.client

url = "http://192.168.1.182:8029"
db  = "odoo19e_dev"
login = "cmarchesseau@aifluencedigital.com"
key = "<api_key_admin>"

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, login, key, {})  # → 2
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
```

## 4. Créer un quality.check depuis les valeurs vNode

```python
# Valeur reçue du tag vNode /HACCP/Frigo_Temperature → 3.5°C
check_id = models.execute_kw(db, uid, key, "quality.check", "create",
    [{"point_id": 1, "measure": 3.5}])

# Lire le résultat automatique
check = models.execute_kw(db, uid, key, "quality.check", "read",
    [[check_id]], {"fields": ["measure", "measure_success", "tolerance_max"]})
# → measure_success = "pass"  (3.5 ≤ 4.0)

# Valider quality_state
models.execute_kw(db, uid, key, "quality.check", "write",
    [[check_id], {"quality_state": check[0]["measure_success"]}])
```

### Logique measure_success (calculée automatiquement par Odoo)

| Champ | Valeur | Signification |
|-------|--------|---------------|
| `measure_success` | `"pass"` | Mesure dans les tolérances du QCP |
| `measure_success` | `"fail"` | Mesure hors tolérances |
| `quality_state` | `"none"` / `"pass"` / `"fail"` | État validé opérateur — à écrire explicitement |

## 5. Créer une quality.alert (alarme HACCP)

```python
alert_id = models.execute_kw(db, uid, key, "quality.alert", "create",
    [{"name": "[HACCP ALERTE] Frigo Positif — 5.8°C > seuil 4°C",
      "description": "Température hors tolérance. Tag vNode: Frigo_Temperature=5.8°C. Max HACCP: 4°C."}])
```

## 6. Script de test complet

```bash
python3 scripts/test-odoo-api.py \
  --url http://192.168.1.182:8029 \
  --db odoo19e_dev \
  --user cmarchesseau@aifluencedigital.com \
  --key <api_key>
```

Sortie attendue (flux vNode → Odoo validé) :
```
[1] Connexion http://192.168.1.182:8029 — DB: odoo19e_dev
    OK — UID: 2
[2] Lecture des QCPs disponibles
    QCP #1: Frigo Positif — Surveillance HACCP
    QCP #2: Congélateur — Surveillance HACCP
    QCP #3: Stockage Sec — Humidité HACCP
[3] Création quality.check test (5.8°C, QCP #1)
    OK — quality.check ID: ...
[4] Création quality.alert test
    OK — quality.alert ID: ...
[5] Vérification quality.check
    measure=5.8 state=fail
OK — API Odoo Qualité fonctionnelle
```

## 7. Simulation flux IoT complet (résultats validés 2026-05-19)

Valeurs vNode tags → quality.checks créés via API :

| Tag vNode | Valeur | QCP | Résultat |
|-----------|--------|-----|----------|
| Frigo_Temperature | 3.5°C | #1 (max 4°C) | **PASS** ✓ |
| Congelateur_Temperature | -18.0°C | #2 (max -15°C) | **PASS** ✓ |
| Stockage_Humidity | 62.1% | #3 (max 75%) | **PASS** ✓ |
| Frigo_Temperature (alerte) | 5.8°C | #1 (max 4°C) | **FAIL** ✗ → quality.alert créée |

`measure_success` est calculé automatiquement par Odoo dès la création du check.

## 8. Créer l'utilisateur responsable restaurant

Settings → Users → New :
- Name : Responsable Cuisine
- Email : responsable@restaurant.fr
- Application accesses : Quality → Administrateur
