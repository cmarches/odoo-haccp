# Serveur Odoo dédié — Configuration et instances

## Présentation du serveur

| Paramètre | Valeur |
|-----------|--------|
| Hostname | ubuntuserver24odoo |
| IP locale | 192.168.1.182 |
| Accès SSH | `ssh christian@192.168.1.182` |
| OS | Ubuntu 24.04 LTS |

## Cartographie des instances Odoo

| Port | Instance | Version | Base de données |
|------|----------|---------|-----------------|
| 8018 | Odoo 18 CE | 18.0 | odoo18_dev (à confirmer) |
| 8019 | Odoo 19 CE | 19.0-20260421 | odoo19_dev |
| 8028 | Odoo 18 EE | 18.0+e | odoo18e_dev (à confirmer) |
| **8029** | **Odoo 19 EE** | **19.0+e-20260421** | **odoo19e_dev** |

Ports complémentaires :
- `8218` / `8228` — Adminer (administration PostgreSQL via navigateur)

**Instance cible POC HACCP : Odoo 19 EE — port 8029**

## Connexion Odoo 19 EE (instance POC HACCP)

| Paramètre | Valeur |
|-----------|--------|
| URL | `http://192.168.1.182:8029` |
| Base de données | `odoo19e_dev` |
| Utilisateur admin | `cmarchesseau@aifluencedigital.com` |
| API Key | Stockée dans `.env` (ne pas committer) |
| UID auth | 2 |

## Modules installés (Odoo 19 EE / odoo19e_dev)

- `quality_control` — Contrôle qualité HACCP (installé 2026-05-19)
- Modules EE standards inclus dans la licence

## Générer une API Key Odoo

```
Settings → Technical → API Keys → New
- Name : vNode HACCP
- Expiration : (vide = permanente)
→ Copier la clé
```

Utiliser cette clé pour tous les appels XML-RPC du POC HACCP.

## Test de connexion API

```bash
python3 - <<'EOF'
import xmlrpc.client
url = "http://192.168.1.182:8029"
db = "odoo19e_dev"
login = "cmarchesseau@aifluencedigital.com"
key = "<api_key>"
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, login, key, {})
print(f"UID: {uid}")  # → 2
EOF
```

## Accès Adminer (PostgreSQL)

```
http://192.168.1.182:8218   (pour l'instance 8018/8028)
http://192.168.1.182:8228   (selon config)
```

Permet d'inspecter les tables directement si nécessaire pour le debug.

## Note sur l'architecture

Les instances Odoo sont installées **en natif** sur le serveur dédié (pas Docker).  
Chaque instance a son propre process Odoo, sa propre base PostgreSQL, et son propre port.  
La gestion des services se fait via systemd : `sudo systemctl status odoo19ee` (à adapter selon le nom du service configuré).
