# VPS Hetzner — Déploiement Odoo 19 CE + ntfy.sh + Webhook Twilio

## 1. Créer le VPS Hetzner
- Console : https://console.hetzner.cloud
- Type : **CX21** (2 vCPU, 4 GB RAM, 40 GB SSD) — ~5€/mois
- OS : Ubuntu 22.04 LTS
- SSH Key : ajouter votre clé publique

## 2. Docker Engine sur Ubuntu 22.04
```bash
ssh root@<ip_vps>

apt update && apt upgrade -y
apt install -y ca-certificates curl gnupg

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
docker --version
```

## 3. Déployer la stack VPS

```bash
mkdir -p /opt/docker/odoo
# Depuis la machine de développement :
scp -r infra/vps/* root@<ip_vps>:/opt/docker/odoo/

# Sur le VPS :
cd /opt/docker/odoo
cp .env.example .env
nano .env   # Remplir POSTGRES_PASSWORD et TWILIO_*

# Démarrer PostgreSQL + Odoo + ntfy.sh d'abord (sans webhook)
docker compose up -d db odoo ntfy
docker compose logs -f odoo
# Attendre : "odoo.service.server: HTTP service (werkzeug) running on ..."
```

## 4. Initialiser la base de données Odoo
```
Ouvrir http://<ip_vps>:8069/web/database/manager
→ Create Database
  - Database Name : odoo
  - Email : admin@aifluencedigital.fr
  - Password : <choisir un password admin sécurisé>
  - Language : French (fr)
  - Country : France
  - Demo data : Non (décoché)
```

## 5. Installer le module Quality Control
```
Apps → Rechercher "Quality Control" → Installer
```
Vérifier : le menu "Quality" apparaît dans la barre de navigation principale.

## 6. Générer une API Key Odoo
```
Settings → Technical → API Keys → New
- Name : vNode HACCP
- Expiration : (vide = permanente)
→ Copier la clé → mettre dans /opt/docker/odoo/.env (ODOO_API_KEY)
```

## 7. Démarrer le webhook Twilio
```bash
docker compose up -d webhook
docker compose logs webhook
```
Expected: `Running on http://0.0.0.0:5000`

## 8. Configurer ntfy.sh

### Mettre à jour server.yml avec l'IP réelle
```bash
# Éditer /opt/docker/odoo/ntfy/server.yml
# Remplacer VOTRE_IP_VPS par l'IP Hetzner réelle
docker compose restart ntfy
```

### Créer l'utilisateur ntfy
```bash
docker exec odoo-ntfy ntfy user add --role=admin haccp-admin
# Saisir un mot de passe sécurisé

docker exec odoo-ntfy ntfy access haccp-admin haccp-alerts rw
```

### Test notification push
```bash
curl -u haccp-admin:<password> \
  -d "Test HACCP ntfy — POC AIFluence Digital" \
  http://<ip_vps>:8080/haccp-alerts
```
Expected : notification reçue dans l'app ntfy sur smartphone.

## 9. Ouvrir les ports firewall VPS
```bash
# Hetzner Firewall (console cloud) → ajouter règles Inbound :
# TCP 8069  — Odoo
# TCP 8080  — ntfy.sh
# TCP 5000  — webhook Twilio
# TCP 22    — SSH
```

## 10. Vérification finale VPS
```bash
docker compose ps
```
Expected :
```
NAME            STATUS
odoo-db         running
odoo-app        running
odoo-ntfy       running
odoo-webhook    running
```
