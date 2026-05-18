#!/bin/bash
# Test abonnement MQTT TTN — vérification réception payloads LHT65.
# Usage: ./test-mqtt-subscribe.sh <ttn_app_id> <ttn_api_key>
# Prérequis: apt install mosquitto-clients

TTN_APP_ID="${1:?Usage: $0 <ttn_app_id> <ttn_api_key>}"
TTN_API_KEY="${2:?Usage: $0 <ttn_app_id> <ttn_api_key>}"

echo "Abonnement MQTT TTN — app: ${TTN_APP_ID}"
echo "Topic: v3/${TTN_APP_ID}@ttn/devices/+/up"
echo "Ctrl+C pour arrêter"
echo "---"

mosquitto_sub \
    --host "eu1.cloud.thethings.network" \
    --port 8883 \
    --capath /etc/ssl/certs \
    --username "${TTN_APP_ID}@ttn" \
    --pw "${TTN_API_KEY}" \
    --topic "v3/${TTN_APP_ID}@ttn/devices/+/up" \
    --verbose
