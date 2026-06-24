#!/bin/bash
# Sets up SSL certificates for production deployment
# Supports: self-signed (for internal ISRO network) or Let's Encrypt (if internet-facing)

set -euo pipefail

CERT_TYPE=${1:-self-signed}   # self-signed | letsencrypt
DOMAIN=${2:-soc.istrac.isro.gov.in}

if [ "$CERT_TYPE" == "self-signed" ]; then
    echo "Generating self-signed certificate for internal ISRO network..."
    mkdir -p certs
    openssl req -x509 -nodes -days 730 -newkey rsa:4096 \
        -keyout certs/server.key -out certs/server.crt \
        -subj "/C=IN/ST=Karnataka/L=Bengaluru/O=ISRO/OU=ISTRAC/CN=$DOMAIN"

    # Generate ES transport/http certificates using ES's certutil
    docker run --rm -v "$(pwd)/certs:/certs" \
        docker.elastic.co/elasticsearch/elasticsearch:8.13.0 \
        bin/elasticsearch-certutil cert --out /certs/elastic-certificates.p12 --pass ""

elif [ "$CERT_TYPE" == "letsencrypt" ]; then
    echo "Requesting Let's Encrypt certificate..."
    docker run --rm -v "$(pwd)/certs:/etc/letsencrypt" \
        certbot/certbot certonly --standalone -d "$DOMAIN" \
        --agree-tos --email soc-admin@istrac.isro.gov.in
fi

echo "✅ Certificates generated in ./certs/"
echo "⚠️  Set proper file permissions: chmod 600 certs/server.key"
chmod 600 certs/server.key
