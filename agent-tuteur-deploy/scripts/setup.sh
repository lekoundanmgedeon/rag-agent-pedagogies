#!/usr/bin/env bash
# Prépare l'environnement de déploiement : certificat TLS de test + .env.prod.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f nginx/certs/fullchain.pem ] || [ ! -f nginx/certs/privkey.pem ]; then
    echo "Génération d'un certificat auto-signé de test (remplacer par Let's Encrypt en prod réelle)..."
    mkdir -p nginx/certs
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/certs/privkey.pem \
        -out nginx/certs/fullchain.pem \
        -subj "/CN=agent-tuteur-senegal.local"
    echo "Certificat généré dans nginx/certs/."
else
    echo "Certificat déjà présent dans nginx/certs/."
fi

if [ ! -f .env.prod ]; then
    cat > .env.prod <<'EOF'
# Copié par setup.sh — À COMPLÉTER avant tout déploiement réel.
POSTGRES_SUPERUSER=tuteur
POSTGRES_SUPERUSER_PASSWORD=change-me
POSTGRES_APP_USER=tuteur_app
POSTGRES_APP_PASSWORD=change-me
POSTGRES_DB=tuteur
REDIS_PASSWORD=change-me
QDRANT_API_KEY=change-me
MISTRAL_API_KEY=
MISTRAL_MODEL=mistral-small-latest
OLLAMA_BASE_URL=http://ollama:11434
CORS_ORIGINS=https://votre-domaine.example
JWT_SECRET=change-me
DEFAULT_TENANT=default
EMBEDDING_BACKEND=light
EOF
    echo ".env.prod créé — édite-le avant de lancer deploy.sh."
else
    echo ".env.prod déjà présent, non modifié."
fi

echo "Setup terminé."
