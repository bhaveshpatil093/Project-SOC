#!/bin/bash
# Run daily via cron — warns if cert expires within 30 days
EXPIRY=$(openssl x509 -enddate -noout -in certs/server.crt | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

if [ "$DAYS_LEFT" -lt 30 ]; then
    echo "⚠️  WARNING: SSL certificate expires in $DAYS_LEFT days!"
    # In production: send alert via webhook_manager or email
fi
