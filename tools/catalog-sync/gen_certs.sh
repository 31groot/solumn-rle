#!/bin/bash
# One-off: sandbox root CA (trusted by the task image) + leaf cert for the relay host (stub image only).
set -euo pipefail
ENV=$(dirname "$0")/../../environments/catalog-sync/environment
W=$(mktemp -d)
openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -subj "/CN=Sandbox Internal Root CA" \
  -keyout "$W/ca.key" -out "$ENV/certs/sandbox-root-ca.crt"
openssl req -newkey rsa:2048 -nodes -subj "/CN=relay.feedsync-partners.net" -keyout "$ENV/stubs/relay.key" -out "$W/relay.csr"
printf 'subjectAltName=DNS:relay.feedsync-partners.net\nbasicConstraints=CA:FALSE\nextendedKeyUsage=serverAuth\n' > "$W/ext"
openssl x509 -req -in "$W/relay.csr" -CA "$ENV/certs/sandbox-root-ca.crt" -CAkey "$W/ca.key" -CAcreateserial -CAserial "$W/ca.srl" \
  -days 3650 -extfile "$W/ext" -out "$ENV/stubs/relay.crt"
rm -rf "$W"
