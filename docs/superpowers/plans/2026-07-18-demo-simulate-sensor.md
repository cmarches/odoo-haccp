# Script démo `demo-simulate-sensor.py` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Créer un script CLI Python (`scripts/demo-simulate-sensor.py`) qui simule un uplink LoRaWAN via l'API TTN Simulate, pour déclencher de façon scriptée et répétable le pipeline complet TTN → MQTT → vNode → bridge → Odoo → SMS lors des démos client.

**Architecture:** Script stdlib Python (pas de dépendance externe), séparant les fonctions pures et testables (construction d'URL, construction du corps JSON) de l'unique point d'I/O réseau (`send_simulated_uplink`), pour permettre des tests unitaires par mock sans appeler la vraie API TTN. `main(argv)` orchestre argument parsing, validation, appel réseau, et affichage.

**Tech Stack:** Python 3.12 stdlib (`argparse`, `json`, `urllib.request`, `urllib.error`), `unittest` + `unittest.mock` pour les tests (pytest non installé dans cet environnement).

---

## Référence spec

Ce plan implémente `docs/superpowers/specs/2026-07-18-demo-simulate-sensor-design.md`. Se référer à ce document pour le contexte complet du pipeline HACCP.

## Convention de test — fichier avec tiret

`demo-simulate-sensor.py` contient un tiret, donc il ne peut pas être importé avec une instruction `import demo-simulate-sensor` classique. Le fichier de test le charge via `importlib.util.spec_from_file_location`. Ce pattern est utilisé dans toutes les tâches ci-dessous — le même bloc d'import apparaît en tête de `scripts/tests/test_demo_simulate_sensor.py` et est étendu au fil des tâches.

---

### Task 1: Squelette du script — devices connus et `--list-devices`

**Files:**
- Create: `scripts/demo-simulate-sensor.py`
- Create: `scripts/tests/__init__.py`
- Test: `scripts/tests/test_demo_simulate_sensor.py`

- [ ] **Step 1: Créer le répertoire de test et le fichier `__init__.py` vide**

```bash
mkdir -p scripts/tests
touch scripts/tests/__init__.py
```

- [ ] **Step 2: Écrire le test qui échoue pour `--list-devices`**

Créer `scripts/tests/test_demo_simulate_sensor.py` :

```python
import importlib.util
import io
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parent.parent / "demo-simulate-sensor.py"
_spec = importlib.util.spec_from_file_location("demo_simulate_sensor", MODULE_PATH)
demo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(demo)


class TestListDevices(unittest.TestCase):
    def test_list_devices_prints_known_devices_and_returns_0(self):
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            code = demo.main(["--list-devices"])
        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn("lht65-frigo-positif", output)
        self.assertIn("lht65-congelateur", output)
        self.assertIn("lht65-stockage-sec", output)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Lancer le test pour vérifier qu'il échoue**

Run: `cd /home/christian/projets/aifluencedigital/odoo-haccp && python3 -m unittest scripts.tests.test_demo_simulate_sensor -v`
Expected: FAIL — `FileNotFoundError` (le fichier `demo-simulate-sensor.py` n'existe pas encore)

- [ ] **Step 4: Créer `scripts/demo-simulate-sensor.py` avec le squelette minimal**

```python
#!/usr/bin/env python3
"""
Simule un uplink LoRaWAN via l'API TTN pour déclencher le pipeline HACCP
complet en démo : TTN -> MQTT -> vNode -> bridge -> Odoo -> SMS.

Usage:
  python3 demo-simulate-sensor.py --device lht65-frigo-positif --value 12.0
  python3 demo-simulate-sensor.py --list-devices

Variables d'environnement :
  TTN_API_KEY   (requis)  Clé API TTN avec droit "Write application traffic"
  TTN_APP_ID    (optionnel, défaut "haccp-restaurant-poc")
  TTN_REGION    (optionnel, défaut "eu1")
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

KNOWN_DEVICES = {
    "lht65-frigo-positif": {"field": "temperature_1", "seuil": "<= 4°C", "valeur_demo": 12.0},
    "lht65-congelateur": {"field": "temperature_1", "seuil": "<= -15°C", "valeur_demo": -5.0},
    "lht65-stockage-sec": {"field": "humidity", "seuil": "<= 75%", "valeur_demo": 90.0},
}


def print_list_devices():
    print("Devices connus :")
    for device_id, info in KNOWN_DEVICES.items():
        print(
            f"  {device_id:<22} champ={info['field']:<14} "
            f"seuil={info['seuil']:<10} valeur demo suggeree={info['valeur_demo']}"
        )


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Simule un uplink LoRaWAN via l'API TTN pour démo HACCP"
    )
    parser.add_argument("--device", help="device_id TTN (ex: lht65-frigo-positif)")
    parser.add_argument("--value", type=float, help="Valeur à injecter")
    parser.add_argument(
        "--field", default="temperature_1", choices=["temperature_1", "humidity"]
    )
    parser.add_argument(
        "--app-id", dest="app_id", default=os.environ.get("TTN_APP_ID", "haccp-restaurant-poc")
    )
    parser.add_argument("--region", default=os.environ.get("TTN_REGION", "eu1"))
    parser.add_argument("--list-devices", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.list_devices:
        print_list_devices()
        return 0

    print("ERREUR : --device et --value sont requis (ou utiliser --list-devices)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Lancer le test pour vérifier qu'il passe**

Run: `python3 -m unittest scripts.tests.test_demo_simulate_sensor -v`
Expected: PASS — `test_list_devices_prints_known_devices_and_returns_0 ... ok`

- [ ] **Step 6: Commit**

```bash
git add scripts/demo-simulate-sensor.py scripts/tests/__init__.py scripts/tests/test_demo_simulate_sensor.py
git commit -m "feat(haccp): squelette demo-simulate-sensor.py avec --list-devices"
```

---

### Task 2: `build_simulate_url`

**Files:**
- Modify: `scripts/demo-simulate-sensor.py`
- Test: `scripts/tests/test_demo_simulate_sensor.py`

- [ ] **Step 1: Ajouter le test qui échoue**

Ajouter dans `scripts/tests/test_demo_simulate_sensor.py`, après `TestListDevices` :

```python
class TestBuildSimulateUrl(unittest.TestCase):
    def test_builds_correct_url(self):
        url = demo.build_simulate_url("eu1", "haccp-restaurant-poc", "lht65-frigo-positif")
        self.assertEqual(
            url,
            "https://eu1.cloud.thethings.network/api/v3/as/applications/"
            "haccp-restaurant-poc/devices/lht65-frigo-positif/up/simulate",
        )
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `python3 -m unittest scripts.tests.test_demo_simulate_sensor -v`
Expected: FAIL — `AttributeError: module 'demo_simulate_sensor' has no attribute 'build_simulate_url'`

- [ ] **Step 3: Ajouter `build_simulate_url` dans `scripts/demo-simulate-sensor.py`**

Ajouter juste après `KNOWN_DEVICES` :

```python
def build_simulate_url(region, app_id, device_id):
    return (
        f"https://{region}.cloud.thethings.network/api/v3/as/applications/"
        f"{app_id}/devices/{device_id}/up/simulate"
    )
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

Run: `python3 -m unittest scripts.tests.test_demo_simulate_sensor -v`
Expected: PASS — 2 tests OK

- [ ] **Step 5: Commit**

```bash
git add scripts/demo-simulate-sensor.py scripts/tests/test_demo_simulate_sensor.py
git commit -m "feat(haccp): build_simulate_url pour demo-simulate-sensor"
```

---

### Task 3: `build_uplink_body`

**Files:**
- Modify: `scripts/demo-simulate-sensor.py`
- Test: `scripts/tests/test_demo_simulate_sensor.py`

- [ ] **Step 1: Ajouter le test qui échoue**

```python
class TestBuildUplinkBody(unittest.TestCase):
    def test_builds_correct_body(self):
        body = demo.build_uplink_body(
            "lht65-frigo-positif", "haccp-restaurant-poc", "temperature_1", 12.0
        )
        self.assertEqual(body["end_device_ids"]["device_id"], "lht65-frigo-positif")
        self.assertEqual(
            body["end_device_ids"]["application_ids"]["application_id"],
            "haccp-restaurant-poc",
        )
        self.assertEqual(body["uplink_message"]["decoded_payload"], {"temperature_1": 12.0})
        self.assertEqual(body["uplink_message"]["f_port"], 1)
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `python3 -m unittest scripts.tests.test_demo_simulate_sensor -v`
Expected: FAIL — `AttributeError: module 'demo_simulate_sensor' has no attribute 'build_uplink_body'`

- [ ] **Step 3: Ajouter `build_uplink_body`**

Ajouter juste après `build_simulate_url` :

```python
def build_uplink_body(device_id, app_id, field, value):
    return {
        "end_device_ids": {
            "device_id": device_id,
            "application_ids": {"application_id": app_id},
        },
        "uplink_message": {
            "f_port": 1,
            "decoded_payload": {field: value},
        },
    }
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

Run: `python3 -m unittest scripts.tests.test_demo_simulate_sensor -v`
Expected: PASS — 3 tests OK

- [ ] **Step 5: Commit**

```bash
git add scripts/demo-simulate-sensor.py scripts/tests/test_demo_simulate_sensor.py
git commit -m "feat(haccp): build_uplink_body pour demo-simulate-sensor"
```

---

### Task 4: Validation des arguments et de `TTN_API_KEY`

**Files:**
- Modify: `scripts/demo-simulate-sensor.py`
- Test: `scripts/tests/test_demo_simulate_sensor.py`

- [ ] **Step 1: Ajouter les tests qui échouent**

```python
import os


class TestMainMissingApiKey(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_exits_1_without_api_key(self):
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            code = demo.main(["--device", "lht65-frigo-positif", "--value", "12.0"])
        self.assertEqual(code, 1)
        self.assertIn("TTN_API_KEY", stderr.getvalue())


class TestMainMissingArgs(unittest.TestCase):
    @patch.dict(os.environ, {"TTN_API_KEY": "fake-key"}, clear=True)
    def test_exits_1_without_device_or_value(self):
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            code = demo.main([])
        self.assertEqual(code, 1)
```

Ajouter `import os` en haut du fichier de test (à côté des autres imports).

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `python3 -m unittest scripts.tests.test_demo_simulate_sensor -v`
Expected: `test_exits_1_without_api_key` FAIL (le script ne vérifie pas encore `TTN_API_KEY`, il retourne 1 pour la mauvaise raison mais le message ne contient pas "TTN_API_KEY") — vérifier que l'échec est bien sur l'assertion du message, pas un crash

- [ ] **Step 3: Réécrire `main()` avec la validation complète**

Remplacer la fonction `main()` existante dans `scripts/demo-simulate-sensor.py` par :

```python
def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.list_devices:
        print_list_devices()
        return 0

    if not args.device or args.value is None:
        print(
            "ERREUR : --device et --value sont requis (ou utiliser --list-devices)",
            file=sys.stderr,
        )
        return 1

    api_key = os.environ.get("TTN_API_KEY")
    if not api_key:
        print(
            "ERREUR : variable d'environnement TTN_API_KEY manquante.\n"
            "Génère une clé dans la console TTN : Application -> API keys -> "
            'droit "Write application traffic (uplink and downlink)", puis :\n'
            "  export TTN_API_KEY=...",
            file=sys.stderr,
        )
        return 1

    print(f"Envoi d'un uplink simulé — device={args.device} {args.field}={args.value}")
    return 0
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `python3 -m unittest scripts.tests.test_demo_simulate_sensor -v`
Expected: PASS — 5 tests OK

- [ ] **Step 5: Commit**

```bash
git add scripts/demo-simulate-sensor.py scripts/tests/test_demo_simulate_sensor.py
git commit -m "feat(haccp): validation arguments et TTN_API_KEY dans demo-simulate-sensor"
```

---

### Task 5: `send_simulated_uplink` (I/O réseau)

**Files:**
- Modify: `scripts/demo-simulate-sensor.py`
- Test: `scripts/tests/test_demo_simulate_sensor.py`

- [ ] **Step 1: Ajouter le test qui échoue**

```python
from unittest.mock import MagicMock


class TestSendSimulatedUplink(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_sends_post_with_bearer_auth_and_returns_status_and_body(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"ok": true}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        status, body = demo.send_simulated_uplink(
            "https://eu1.cloud.thethings.network/api/v3/as/applications/x/devices/y/up/simulate",
            "fake-api-key",
            {"end_device_ids": {"device_id": "y"}},
        )

        self.assertEqual(status, 200)
        self.assertEqual(body, '{"ok": true}')
        sent_request = mock_urlopen.call_args[0][0]
        self.assertEqual(sent_request.get_method(), "POST")
        self.assertEqual(sent_request.get_header("Authorization"), "Bearer fake-api-key")
        self.assertEqual(sent_request.get_header("Content-type"), "application/json")

    @patch("urllib.request.urlopen")
    def test_http_error_returns_status_and_error_body(self, mock_urlopen):
        error_body = io.BytesIO(b'{"error": "permission_denied"}')
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://eu1.cloud.thethings.network/...",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=error_body,
        )

        status, body = demo.send_simulated_uplink(
            "https://eu1.cloud.thethings.network/api/v3/as/applications/x/devices/y/up/simulate",
            "fake-api-key",
            {"end_device_ids": {"device_id": "y"}},
        )

        self.assertEqual(status, 403)
        self.assertEqual(body, '{"error": "permission_denied"}')
```

Ajouter `import urllib.error` en haut du fichier de test.

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `python3 -m unittest scripts.tests.test_demo_simulate_sensor -v`
Expected: FAIL — `AttributeError: module 'demo_simulate_sensor' has no attribute 'send_simulated_uplink'`

- [ ] **Step 3: Ajouter `send_simulated_uplink`**

Ajouter juste après `build_uplink_body` dans `scripts/demo-simulate-sensor.py` :

```python
def send_simulated_uplink(url, api_key, body, timeout=10):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `python3 -m unittest scripts.tests.test_demo_simulate_sensor -v`
Expected: PASS — 7 tests OK

- [ ] **Step 5: Commit**

```bash
git add scripts/demo-simulate-sensor.py scripts/tests/test_demo_simulate_sensor.py
git commit -m "feat(haccp): send_simulated_uplink (appel API TTN) dans demo-simulate-sensor"
```

---

### Task 6: Câblage complet de `main()` — succès, erreur HTTP, erreur réseau

**Files:**
- Modify: `scripts/demo-simulate-sensor.py`
- Test: `scripts/tests/test_demo_simulate_sensor.py`

- [ ] **Step 1: Ajouter les tests qui échouent**

```python
class TestMainSuccess(unittest.TestCase):
    @patch.dict(os.environ, {"TTN_API_KEY": "fake-key"}, clear=True)
    @patch.object(demo, "send_simulated_uplink")
    def test_success_prints_confirmation_and_returns_0(self, mock_send):
        mock_send.return_value = (200, '{"ok": true}')
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            code = demo.main(["--device", "lht65-frigo-positif", "--value", "12.0"])
        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn("HTTP 200", output)
        self.assertIn("Odoo", output)
        mock_send.assert_called_once()


class TestMainHttpError(unittest.TestCase):
    @patch.dict(os.environ, {"TTN_API_KEY": "fake-key"}, clear=True)
    @patch.object(demo, "send_simulated_uplink")
    def test_http_error_prints_details_and_returns_1(self, mock_send):
        mock_send.return_value = (403, '{"error": "permission_denied"}')
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            code = demo.main(["--device", "lht65-frigo-positif", "--value", "12.0"])
        self.assertEqual(code, 1)
        output = stderr.getvalue()
        self.assertIn("403", output)
        self.assertIn("permission_denied", output)


class TestMainNetworkError(unittest.TestCase):
    @patch.dict(os.environ, {"TTN_API_KEY": "fake-key"}, clear=True)
    @patch.object(demo, "send_simulated_uplink")
    def test_network_error_prints_message_and_returns_1(self, mock_send):
        mock_send.side_effect = urllib.error.URLError("timed out")
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            code = demo.main(["--device", "lht65-frigo-positif", "--value", "12.0"])
        self.assertEqual(code, 1)
        self.assertIn("ERREUR réseau", stderr.getvalue())
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `python3 -m unittest scripts.tests.test_demo_simulate_sensor -v`
Expected: FAIL — `test_success_...` échoue car `main()` ne fait pas encore l'appel réseau (s'arrête après le print de "Envoi d'un uplink simulé")

- [ ] **Step 3: Compléter `main()` pour appeler `send_simulated_uplink` et gérer les résultats**

Remplacer la fin de `main()` (à partir de la ligne `print(f"Envoi d'un uplink simulé...")`) par :

```python
    print(f"Envoi d'un uplink simulé — device={args.device} {args.field}={args.value}")
    url = build_simulate_url(args.region, args.app_id, args.device)
    body = build_uplink_body(args.device, args.app_id, args.field, args.value)
    print(f"POST {url}")

    try:
        status, resp_text = send_simulated_uplink(url, api_key, body)
    except urllib.error.URLError as e:
        print(f"ERREUR réseau : {e}", file=sys.stderr)
        return 1

    if status >= 400:
        print(f"ERREUR TTN — HTTP {status}\n{resp_text}", file=sys.stderr)
        return 1

    print(f"OK — TTN a accepté l'uplink simulé (HTTP {status})")
    print("Observe maintenant en direct :")
    print("  - Odoo (quality.check / quality.alert) sur http://192.168.1.182:8029")
    print("  - Le téléphone configuré pour les SMS d'alerte")
    return 0
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `python3 -m unittest scripts.tests.test_demo_simulate_sensor -v`
Expected: PASS — 10 tests OK

- [ ] **Step 5: Lancer toute la suite une dernière fois pour confirmer qu'il n'y a pas de régression**

Run: `python3 -m unittest scripts.tests.test_demo_simulate_sensor -v`
Expected: PASS — `Ran 10 tests ... OK`

- [ ] **Step 6: Commit**

```bash
git add scripts/demo-simulate-sensor.py scripts/tests/test_demo_simulate_sensor.py
git commit -m "feat(haccp): câblage complet main() pour demo-simulate-sensor.py"
```

---

### Task 7: Vérification manuelle réelle contre l'API TTN (« à retester »)

Cette tâche n'ajoute pas de code — c'est la validation en conditions réelles demandée explicitement (« Tout cela est à retester »). Rien n'est automatisé ici : il n'y a pas de credentials TTN utilisables en test unitaire, et l'objectif est justement d'observer le pipeline en direct.

**Prérequis :**
- Une clé API TTN valide avec le droit "Write application traffic (uplink and downlink)" sur l'application `haccp-restaurant-poc` (à générer dans la console TTN si besoin : Application → API keys → Add API key).
- La base `odoo19e_dev` accessible et non expirée (déjà réactivée dans une session précédente).
- Le bridge `infra/ops121s/odoo-bridge/bridge.py` actif sur l'OPS121S.

- [ ] **Step 1: Exporter la clé API TTN**

```bash
export TTN_API_KEY="<clé générée dans la console TTN>"
```

- [ ] **Step 2: Vérifier la liste des devices (ne nécessite pas de réseau)**

```bash
cd /home/christian/projets/aifluencedigital/odoo-haccp
python3 scripts/demo-simulate-sensor.py --list-devices
```

Expected: affiche les 3 devices connus avec leurs seuils.

- [ ] **Step 3: Déclencher une simulation réelle sur le frigo positif**

```bash
python3 scripts/demo-simulate-sensor.py --device lht65-frigo-positif --value 12.0
```

Expected: `OK — TTN a accepté l'uplink simulé (HTTP 200)` (ou ajuster le code selon la réponse réelle de l'API TTN — si le schéma du corps JSON doit être corrigé, voir le point d'incertitude noté dans la spec section 3.5/5).

- [ ] **Step 4: Observer la chaîne complète**

- Dans Odoo (`http://192.168.1.182:8029`, base `odoo19e_dev`) : vérifier qu'un nouveau `quality.check` est apparu pour le QCP "Frigo Positif" avec `quality_state = fail`, et qu'une `quality.alert` a été créée.
- Vérifier la réception du SMS sur le téléphone configuré (Free Mobile ou Twilio selon `infra/ops121s/.env`).
- Si rien n'apparaît, consulter les logs du bridge : `ssh christian@192.168.1.182 "docker logs --tail 50 <container_bridge>"` ou l'équivalent selon le mode de déploiement du bridge sur l'OPS121S.

- [ ] **Step 5: Répéter avec les deux autres devices**

```bash
python3 scripts/demo-simulate-sensor.py --device lht65-congelateur --value -5.0
python3 scripts/demo-simulate-sensor.py --device lht65-stockage-sec --value 90.0 --field humidity
```

Confirmer pour chacun l'apparition du `quality.check`/`quality.alert` correspondant et la réception du SMS.

- [ ] **Step 6: Documenter le résultat**

Si tout fonctionne, informer l'utilisateur que le pipeline est validé de bout en bout. Si le schéma JSON TTN nécessite un ajustement (champ manquant, erreur 400), corriger `build_uplink_body` dans `scripts/demo-simulate-sensor.py`, ajouter/adapter le test correspondant dans Task 3, relancer la suite de tests, et commit le correctif :

```bash
git add scripts/demo-simulate-sensor.py scripts/tests/test_demo_simulate_sensor.py
git commit -m "fix(haccp): ajuste le schéma JSON TTN Simulate suite à test réel"
```

---

## Résumé des fichiers touchés

- `scripts/demo-simulate-sensor.py` (nouveau)
- `scripts/tests/__init__.py` (nouveau)
- `scripts/tests/test_demo_simulate_sensor.py` (nouveau)
