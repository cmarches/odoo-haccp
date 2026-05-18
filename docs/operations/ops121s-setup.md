# OPS121S — Installation Ubuntu 20.04 LTS + Docker Engine + Stack HACCP

## 1. Installation Ubuntu 20.04 LTS Server
- ISO : ubuntu-20.04.6-live-server-amd64.iso
- Partitionnement : LVM auto (tout le SSD 256 GB)
- Packages à l'installation : OpenSSH Server uniquement
- Hostname : ops121s-haccp
- User principal : haccp

Note production : Ubuntu 20.04 est hors support standard depuis avril 2025.
Migrer vers 22.04 LTS avant tout déploiement client réel.

## 2. Post-installation
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git sqlite3 restic mosquitto-clients
```

## 3. Docker Engine sur Ubuntu 20.04
```bash
# Supprimer anciens packages
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Dépendances
sudo apt install -y ca-certificates gnupg lsb-release

# Clé GPG Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Repo Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Vérification
docker --version
docker compose version
```

Expected :
```
Docker version 26.x.x, build ...
Docker Compose version v2.x.x
```

## 4. Permissions Docker
```bash
sudo usermod -aG docker haccp
newgrp docker
docker run --rm hello-world
```
Expected: `Hello from Docker!`

## 5. Déployer la stack HACCP

```bash
# Copier les fichiers depuis le dépôt git
sudo mkdir -p /opt/docker/haccp
sudo chown haccp:haccp /opt/docker/haccp

# Depuis la machine de développement :
scp -r infra/ops121s/* haccp@10.10.10.10:/opt/docker/haccp/

# Sur l'OPS121S :
cd /opt/docker/haccp
cp .env.example .env
nano .env   # Remplir INFLUXDB_USER, INFLUXDB_PASSWORD, INFLUXDB_TOKEN

# Démarrer Mosquitto + InfluxDB + Portainer (sans vNode dans un premier temps)
docker compose up -d mosquitto influxdb portainer
docker compose ps
```

Expected :
```
NAME                STATUS
haccp-mosquitto     running
haccp-influxdb      running
haccp-portainer     running
```

## 6. Vérification Mosquitto
```bash
# Pub/sub local (deux terminaux)
mosquitto_sub -h localhost -p 1883 -t "test/#" &
mosquitto_pub -h localhost -p 1883 -t "test/haccp" -m '{"temp":3.5}'
```
Expected: `{"temp":3.5}` s'affiche dans le subscriber. Ctrl+C pour arrêter.

## 7. Vérification InfluxDB
```bash
# Depuis le VLAN Management : http://10.10.10.10:8086
# Login : INFLUXDB_USER / INFLUXDB_PASSWORD
# Vérifier que le bucket "haccp" est présent
```

## 8. Portainer
```bash
# https://10.10.10.10:9443 — créer le compte admin au premier accès
# Vérifier les 3 containers Running
```

## 9. Ajouter vNode à la stack
```bash
# Une fois l'image vNode obtenue auprès de Vester :
# 1. Charger l'image : docker load -i vnode-automation.tar
# 2. Mettre à jour l'image dans docker-compose.yml
docker compose up -d vnode
docker compose logs vnode   # Vérifier démarrage (mode démo : redémarre toutes les 2h)
```
