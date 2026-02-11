#!/bin/bash
set -eo pipefail

# Merge any CA certs mounted at /usr/local/share/ca-certificates (e.g. by Kubernetes
# when CA_CERT_SECRET_NAME is set) into the system trust store so outbound HTTPS
# (e.g. to Azure OpenAI, webhook callbacks) can verify corporate/internal TLS.
if command -v update-ca-certificates &>/dev/null; then
  update-ca-certificates
fi

exec "$@"
