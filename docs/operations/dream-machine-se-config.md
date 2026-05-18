# Dream Machine SE — Configuration réseau HACCP

## Accès UniFi OS
- URL : https://192.168.1.1 (IP par défaut — changer immédiatement)
- Login initial : ubnt / ubnt

## 1. Dual WAN — Failover 4G/LTE (1NCE SIM)

Settings → Internet → WAN1 :
- Protocol : DHCP (ou PPPoE selon ISP)

Settings → Internet → WAN2 (SIM 1NCE) :
- Type : USB 4G LTE ou module SIM selon version UDM SE
- Mode : **Failover** (pas Load Balance)
- APN : `iot.1nce.net` (confirmer dans le portail 1NCE)
- Ping target : 8.8.8.8 (détection coupure)
- Failover delay : 30s

La nano-SIM 1NCE s'insère dans le slot SIM du Dream Machine SE.

## 2. VLANs

### VLAN 10 — IoT HACCP
Settings → Networks → Add Network :
- Name : IoT_HACCP
- VLAN ID : 10
- Subnet : 10.10.10.0/24
- DHCP : Enabled — Range 10.10.10.100–10.10.10.200
- DNS : 10.10.10.1
- Inter-VLAN routing : **Disabled** (isolation IoT)

### VLAN 20 — Wi-Fi Restaurant
- Name : WiFi_Restaurant
- VLAN ID : 20
- Subnet : 10.10.20.0/24
- DHCP : Enabled — Range 10.10.20.100–10.10.20.250

### VLAN 30 — Management
- Name : Management
- VLAN ID : 30
- Subnet : 10.10.30.0/24
- DHCP : Disabled (IPs fixes)

## 3. Affectation des ports PoE

| Port | Équipement | VLAN natif | PoE |
|------|-----------|-----------|-----|
| Port 1 | RAK7268 Gateway | 10 (IoT) | Activé (802.3af) |
| Port 2 | OPS121S | 10 (IoT) | Désactivé (alim. propre) |
| Port 8 | Switch management | 30 | Désactivé |

Settings → Switch Ports → Port 1 → Native VLAN : 10, PoE : Enabled.

## 4. Règle firewall — Isolation IoT ↔ Wi-Fi

Settings → Firewall → Rules → Create :
- Name : Block_IoT_to_WiFi
- Source : Network IoT_HACCP (10.10.10.0/24)
- Destination : Network WiFi_Restaurant (10.10.20.0/24)
- Action : Drop

## 5. IP fixes (DHCP reservations)

Settings → Networks → IoT_HACCP → DHCP Reservations :
- MAC RAK7268 → IP fixe 10.10.10.11
- MAC OPS121S → IP fixe 10.10.10.10

## 6. Vérification

Depuis OPS121S (10.10.10.10) :
```bash
# Accès Internet via Fibre (WAN1)
ping -c 4 8.8.8.8

# Test failover : débrancher câble WAN1, attendre 35s, vérifier continuité
ping -c 30 -i 2 8.8.8.8
# Les paquets doivent reprendre après ~30s (bascule sur 4G/LTE)

# Vérifier isolation VLAN : depuis IoT, la gateway Wi-Fi ne doit pas répondre
ping -c 2 10.10.20.1
# Expected: 100% packet loss (règle firewall)
```
