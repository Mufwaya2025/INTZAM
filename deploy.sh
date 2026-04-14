#!/bin/bash
# =============================================================================
#  IntZam LMS — Production Deploy Script
#  Run this on your Ubuntu server after cloning the repo.
#
#  Usage:
#      chmod +x deploy.sh
#      ./deploy.sh
# =============================================================================

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  IntZam LMS — Production Deployment   ${NC}"
echo -e "${BLUE}========================================${NC}"

# ── Check Docker ──────────────────────────────────────────────────────────────
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker not found. Installing...${NC}"
    curl -fsSL https://get.docker.com | bash
    sudo usermod -aG docker $USER
    echo -e "${YELLOW}Docker installed. Please log out and back in, then re-run this script.${NC}"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo -e "${RED}Docker Compose plugin not found. Installing...${NC}"
    sudo apt-get update && sudo apt-get install -y docker-compose-plugin
fi

echo -e "${GREEN}✔ Docker is ready${NC}"

# ── Check .env files ──────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠ Created .env from .env.example — please fill in your values:${NC}"
    echo -e "  nano .env"
    echo -e "${YELLOW}Then re-run: ./deploy.sh${NC}"
    exit 1
fi

if grep -q "CHANGE_ME" .env; then
    echo -e "${RED}✗ .env still has CHANGE_ME placeholders. Fill them in first:${NC}"
    echo -e "  nano .env"
    exit 1
fi

if [ ! -f "backend/.env.production" ]; then
    echo -e "${RED}✗ backend/.env.production is missing.${NC}"
    echo -e "  Copy and fill it in: nano backend/.env.production"
    exit 1
fi

if grep -q "CHANGE_ME" backend/.env.production; then
    echo -e "${RED}✗ backend/.env.production still has CHANGE_ME placeholders.${NC}"
    echo -e "  nano backend/.env.production"
    exit 1
fi

if [ ! -f "website/.env.production" ]; then
    cp website/.env.production.example website/.env.production
    echo -e "${YELLOW}⚠ Created website/.env.production — please fill in your values:${NC}"
    echo -e "  nano website/.env.production"
    echo -e "${YELLOW}Then re-run: ./deploy.sh${NC}"
    exit 1
fi

if grep -q "CHANGE_ME" website/.env.production; then
    echo -e "${RED}✗ website/.env.production still has CHANGE_ME placeholders.${NC}"
    echo -e "  nano website/.env.production"
    exit 1
fi

echo -e "${GREEN}✔ All environment files are ready${NC}"

# ── Check nginx domain ────────────────────────────────────────────────────────
if grep -q "YOUR_DOMAIN" nginx/nginx.conf; then
    echo -e "${YELLOW}⚠ Remember to replace YOUR_DOMAIN in nginx/nginx.conf with your actual domain.${NC}"
    echo -e "  nano nginx/nginx.conf"
    read -p "  Have you already done this? (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        exit 1
    fi
fi

# ── Create second database for website ───────────────────────────────────────
echo -e "${BLUE}Starting database...${NC}"
docker compose -f docker-compose.prod.yml up -d db
echo "Waiting for PostgreSQL to be ready..."
sleep 8

DB_PASSWORD=$(grep DB_PASSWORD .env | cut -d '=' -f2)
echo -e "${BLUE}Creating website database if it doesn't exist...${NC}"
docker compose -f docker-compose.prod.yml exec db \
    psql -U intzam_user -d intzam_lms -tc \
    "SELECT 1 FROM pg_database WHERE datname='intzam_website'" | grep -q 1 || \
docker compose -f docker-compose.prod.yml exec db \
    psql -U intzam_user -c "CREATE DATABASE intzam_website;" || true

# ── Build and start all services ──────────────────────────────────────────────
echo -e "${BLUE}Building and starting all services...${NC}"
docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment complete!                  ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Services running:"
docker compose -f docker-compose.prod.yml ps
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Get SSL certificate:"
echo -e "     docker compose -f docker-compose.prod.yml run --rm certbot certonly \\"
echo -e "       --webroot -w /var/www/certbot -d YOUR_DOMAIN --email YOUR_EMAIL --agree-tos"
echo -e "  2. Reload nginx:"
echo -e "     docker compose -f docker-compose.prod.yml exec nginx nginx -s reload"
echo -e "  3. View logs:"
echo -e "     docker compose -f docker-compose.prod.yml logs -f"
