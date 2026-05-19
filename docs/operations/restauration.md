# Restauration HACCP — Procédure de reprise

Couvre tous les scénarios de panne : OPS121S hors service, NAS inaccessible, corruption Restic.

---

## Priorité des sauvegardes

```
Niveau 1 — Restic (Synology NAS)    → config + bridge + scripts, quotidien
Niveau 2 — GitHub (odoo-haccp)      → config .n3c + bridge.py + scripts
Niveau 3 — Gestionnaire de secrets  → bridge.env (credentials, hors Git)
```

> **bridge.env n'est jamais dans Git** (contient les clés API et mots de passe).  
> Il doit être sauvegardé séparément dans un gestionnaire de secrets (voir §4).

---

## Scénario 1 — OPS121S HS, NAS disponible (cas normal)

### 1.1 Remplacer le matériel

Installer un nouvel OPS121S, lui assigner la même IP fixe que l'ancien.

### 1.2 Installer Restic

```bash
VER=$(curl -s https://api.github.com/repos/restic/restic/releases/latest | grep tag_name | cut -d'"' -f4 | tr -d 'v')
curl -LO "https://github.com/restic/restic/releases/download/v${VER}/restic_${VER}_linux_arm64.bz2"
bunzip2 restic_${VER}_linux_arm64.bz2
mv restic_${VER}_linux_arm64 /usr/local/bin/restic
chmod +x /usr/local/bin/restic
```

### 1.3 Lister les snapshots disponibles

```bash
restic \
  -r sftp:christian@192.168.1.174:/home/restic-repos/ops121s-haccp \
  --password-file /root/.restic-password \
  snapshots
```

Sortie attendue :
```
ID        Time                 Host          Tags
------------------------------------------------------
f13dbf40  2026-05-19 03:00:01  centralserver ops121s,haccp
a2b5c891  2026-05-20 03:00:02  centralserver ops121s,haccp
```

### 1.4 Restaurer le dernier snapshot

```bash
restic \
  -r sftp:christian@192.168.1.174:/home/restic-repos/ops121s-haccp \
  --password-file /root/.restic-password \
  restore latest \
  --target /
```

Cela restaure :
- `/home/christian/haccp/vnode/config/` → tous les `.n3c`
- `/home/christian/haccp/odoo-bridge/bridge.py`
- `/home/christian/haccp/haccp-backup.sh`

> `bridge.env` n'est **pas** restauré par Restic (exclu volontairement). Le recréer depuis §4.

### 1.5 Redémarrer les services

```bash
systemctl daemon-reload
systemctl enable --now vnode haccp-odoo-bridge haccp-backup.timer
systemctl status vnode haccp-odoo-bridge
```

---

## Scénario 2 — NAS inaccessible ou Restic indisponible

Fallback : restaurer depuis **GitHub**.

### 2.1 Cloner le repo

```bash
opkg install git  # si nécessaire sur OPS121S
git clone https://github.com/cmarches/odoo-haccp.git /tmp/odoo-haccp
```

### 2.2 Restaurer les fichiers vNode

```bash
mkdir -p /home/christian/haccp/vnode/config
cp /tmp/odoo-haccp/infra/ops121s/vnode/config/*.n3c \
   /home/christian/haccp/vnode/config/
```

### 2.3 Restaurer le bridge

```bash
mkdir -p /home/christian/haccp/odoo-bridge
cp /tmp/odoo-haccp/infra/ops121s/odoo-bridge/bridge.py \
   /home/christian/haccp/odoo-bridge/
cp /tmp/odoo-haccp/infra/ops121s/haccp-backup.sh \
   /home/christian/haccp/
chmod +x /home/christian/haccp/haccp-backup.sh
```

### 2.4 Recréer bridge.env depuis le gestionnaire de secrets (§4)

```bash
cat > /home/christian/haccp/odoo-bridge/bridge.env <<'EOF'
ODOO_URL=...
ODOO_DB=...
ODOO_LOGIN=...
ODOO_KEY=...
BRIDGE_PORT=5001
FREE_MOBILE_USER=...
FREE_MOBILE_KEY=...
EOF
chmod 600 /home/christian/haccp/odoo-bridge/bridge.env
```

### 2.5 Recréer les services systemd et redémarrer

Suivre §1.5 ci-dessus.

---

## Scénario 3 — Corruption du dépôt Restic

### 3.1 Vérifier l'état du dépôt

```bash
restic \
  -r sftp:christian@192.168.1.174:/home/restic-repos/ops121s-haccp \
  --password-file /root/.restic-password \
  check
```

### 3.2 Tenter une réparation de l'index

```bash
restic \
  -r sftp:christian@192.168.1.174:/home/restic-repos/ops121s-haccp \
  --password-file /root/.restic-password \
  rebuild-index
```

Relancer `check` après. Si l'erreur persiste → passer au Scénario 2 (GitHub).

### 3.3 Réinitialiser le dépôt Restic (dernier recours)

Si le dépôt est irrécupérable, supprimer et réinitialiser :

```bash
# Sur le NAS Synology — via SSH
rm -rf /home/restic-repos/ops121s-haccp
mkdir -p /home/restic-repos/ops121s-haccp

# Sur OPS121S
restic \
  -r sftp:christian@192.168.1.174:/home/restic-repos/ops121s-haccp \
  --password-file /root/.restic-password \
  init

# Lancer un backup immédiat
/home/christian/haccp/haccp-backup.sh
```

---

## 4. Gestion des secrets (bridge.env)

`bridge.env` contient les clés API et ne doit jamais être dans Git. Il doit être sauvegardé dans un gestionnaire de secrets.

### Recommandation : Bitwarden (gratuit, auto-hébergeable)

Créer une **Note Sécurisée** par client dans Bitwarden :

```
Titre   : HACCP bridge.env — <Nom Client>
Dossier : AIFluence / HACCP
Contenu :
  ODOO_URL=...
  ODOO_DB=...
  ODOO_LOGIN=...
  ODOO_KEY=...
  BRIDGE_PORT=5001
  FREE_MOBILE_USER=...
  FREE_MOBILE_KEY=...
```

**Alternative simple** : fichier chiffré avec GPG sur le NAS :

```bash
# Chiffrer
gpg --symmetric --cipher-algo AES256 bridge.env
# → bridge.env.gpg (copier sur NAS manuellement)

# Déchiffrer lors d'une restauration
gpg -d bridge.env.gpg > bridge.env
chmod 600 bridge.env
```

---

## 5. Checklist post-restauration

Après toute restauration, valider le pipeline complet :

```bash
# 1. Test bridge direct
curl -s -X POST http://127.0.0.1:5001/quality-check \
  -H "Content-Type: application/json" \
  -d '{"qcp_id": 1, "value": 3.5, "tag": "Frigo_Temperature", "quality": 192}'
# Attendu : {"status":"ok","result":"pass"}

# 2. Test FAIL + SMS
curl -s -X POST http://127.0.0.1:5001/quality-check \
  -H "Content-Type: application/json" \
  -d '{"qcp_id": 1, "value": 6.0, "tag": "Frigo_Temperature", "quality": 192}'
# Attendu : {"status":"ok","result":"fail"} + SMS reçu

# 3. Vérifier les services
systemctl status vnode haccp-odoo-bridge haccp-backup.timer

# 4. Vérifier logs bridge
journalctl -u haccp-odoo-bridge --since "5 minutes ago"
```

- [ ] Bridge répond au test PASS
- [ ] Bridge répond au test FAIL + quality.alert créée dans Odoo
- [ ] SMS reçu sur le téléphone du responsable
- [ ] vNode WebUI accessible : `http://<ip-ops121s>:8003`
- [ ] Tags mis à jour dans vNode après un uplink TTN (Simulate ou réel)
- [ ] Restic re-initialisé et premier snapshot vérifié
