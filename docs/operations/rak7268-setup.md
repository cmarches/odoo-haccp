# RAK7268 — Configuration gateway LoRaWAN EU868

## Connexion
- Brancher Port 1 du Dream Machine SE (PoE 802.3af) → RAK7268
- IP assignée par DHCP IoT VLAN → vérifier dans UniFi : Clients → 10.10.10.11
- WebUI : http://10.10.10.11 — Login : root / root (changer immédiatement)

## 1. Fréquence
LoRa Network → LoRaWAN Network Settings :
- Region : **EU868**
- Channel plan : EU868 (8 canaux standard TTN)

## 2. Connexion TTN (Basics Station — recommandé)
LoRa Network → Network Settings → Packet Forwarder → Basic Station :
- LNS URI : `wss://eu1.cloud.thethings.network:8887`
- CUPS URI : `https://eu1.cloud.thethings.network:443`
- Trust Certificate : laisser vide (certificat Let's Encrypt public)
- Gateway key : récupérée dans TTN Console (voir ttn-setup.md section 3)

Alternative (UDP Packet Forwarder si Basic Station non disponible) :
- Server Address : `eu1.cloud.thethings.network`
- Server Port : 1700

## 3. Vérification
Dashboard RAK7268 → LoRa Packet Logger :
- Après activation des LHT65, des paquets `uplink` doivent apparaître
- RSSI typique restaurant : -80 à -100 dBm
- SNR > 5 dB = signal acceptable

## 4. Conseil position
Placer la gateway en hauteur (2m+), proche du centre du restaurant.
Le LoRaWAN EU868 passe sans problème les cloisons et les portes de frigo.
