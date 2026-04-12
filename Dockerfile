# syntax=docker/dockerfile:1

# Node konfigurácia:
# - predvolené: 24.12 (LTS)
# - alternatíva: 25.2
# Pri build-e môžeš prepísať napr.:
# --build-arg NODE_IMAGE=node:25.2-slim --build-arg NODE_SETUP_MAJOR=25
ARG NODE_IMAGE=node:24.12-slim
ARG NODE_SETUP_MAJOR=24

# ─────────────────────────────────────────
# Stage: check
# ─────────────────────────────────────────
FROM python:3.14-slim AS check

# Python závislosti pre interpreter + nástroje statickej kontroly
COPY python/int/requirements.txt /tmp/requirements.txt
COPY python/int/requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/requirements-dev.txt \
    && rm -f /tmp/requirements.txt /tmp/requirements-dev.txt

# Node.js + npm pre TypeScript nástroje (tester)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_SETUP_MAJOR}.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /src

# Adresáre budú pripojené ako bind mount za behu:
#   --mount type=bind,source=./python/int,target=/src/int
#   --mount type=bind,source=./typescript/tester,target=/src/tester

CMD ["bash"]


# ─────────────────────────────────────────
# Stage: build
# ─────────────────────────────────────────
FROM ${NODE_IMAGE} AS build

WORKDIR /src/tester

# Skopíruj zdrojový kód testeru a preloż ho
COPY typescript/tester/package*.json ./
RUN npm ci

COPY typescript/tester/ ./
RUN npm run build


# ─────────────────────────────────────────
# Stage: runtime
# ─────────────────────────────────────────
FROM python:3.14-slim AS runtime

WORKDIR /app

# Skopíruj iba zdrojový kód Pythonu (nie dev závislosti)
COPY python/int/ ./

# Inštaluj len runtime závislosti (ak existujú)
RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# CLI vstupný bod je src/solint.py (balík interpreter je relatívny k tomuto adresáru)
WORKDIR /app/src
ENTRYPOINT ["python", "solint.py"]


# ─────────────────────────────────────────
# Stage: test
# ─────────────────────────────────────────
FROM runtime AS test

# Node ako v stage build/check (predvolený balík z Debianu je zvyčajne starší)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_SETUP_MAJOR}.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /tester

# Skopíruj preložený tester z build stage
COPY --from=build /src/tester/dist ./dist
COPY --from=build /src/tester/node_modules ./node_modules
COPY --from=build /src/tester/package.json ./

ENTRYPOINT ["node", "dist/tester.js"]