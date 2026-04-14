# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Accept build-time API URL
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

COPY package*.json ./
RUN npm ci --silent

COPY . .
RUN npm run build

# ── Stage 2: Export dist ───────────────────────────────────────────────────────
# The dist/ output is picked up by nginx via a shared Docker volume.
FROM alpine:3.19
WORKDIR /app
COPY --from=builder /app/dist ./dist
CMD ["sh", "-c", "cp -r /app/dist/. /output/ && echo 'Client PWA dist ready.'"]
