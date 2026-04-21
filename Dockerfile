# syntax=docker/dockerfile:1
# Created by <xbujdot00> with Generative AI


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

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY python/int/requirements.txt /tmp/requirements.txt
COPY python/int/requirements-dev.txt /tmp/requirements-dev.txt
COPY sol2xml/requirements.txt /tmp/sol2xml-requirements.txt
RUN pip install --no-cache-dir \
    -r /tmp/requirements.txt \
    -r /tmp/requirements-dev.txt \
    -r /tmp/sol2xml-requirements.txt \
    && rm -f /tmp/requirements.txt /tmp/requirements-dev.txt /tmp/sol2xml-requirements.txt

# Node.js + npm pre TypeScript nástroje (tester)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_SETUP_MAJOR}.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /src

# Zadanie: spustiteľné wrappery cez ./ruff a ./mypy
RUN printf '%s\n' '#!/bin/sh' 'set -eu' 'cd /src/int' 'if [ "$#" -eq 0 ]; then exec ruff check src; fi' 'exec ruff "$@"' > /src/ruff \
    && chmod +x /src/ruff \
    && printf '%s\n' '#!/bin/sh' 'set -eu' 'cd /src/int' 'if [ "$#" -eq 0 ]; then exec mypy src; fi' 'exec mypy "$@"' > /src/mypy \
    && chmod +x /src/mypy \
    && printf '%s\n' '#!/bin/sh' 'set -eu' 'cd /src/tester' 'if [ ! -x node_modules/.bin/eslint ]; then npm ci; fi' 'exec npm exec -- eslint -- "$@"' > /usr/local/bin/eslint \
    && chmod +x /usr/local/bin/eslint \
    && printf '%s\n' '#!/bin/sh' 'set -eu' 'cd /src/tester' 'if [ ! -x node_modules/.bin/prettier ]; then npm ci; fi' 'exec npm exec -- prettier -- "$@"' > /usr/local/bin/prettier \
    && chmod +x /usr/local/bin/prettier

# Adresáre budú pripojené ako bind mount za behu:
#   --mount type=bind,source=./python/int,target=/src/int
#   --mount type=bind,source=./typescript/tester,target=/src/tester

ENTRYPOINT ["/bin/sh"]


# ─────────────────────────────────────────
# Stage: build-test
# ─────────────────────────────────────────
FROM ${NODE_IMAGE} AS build-test

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

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Skopíruj iba zdrojový kód Pythonu (nie dev závislosti)
COPY python/int/ ./

# Inštaluj len runtime závislosti (ak existujú)
RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    fi
COPY sol2xml/requirements.txt /tmp/sol2xml-requirements.txt
RUN pip install --no-cache-dir -r /tmp/sol2xml-requirements.txt \
    && rm -f /tmp/sol2xml-requirements.txt

# CLI vstupný bod je src/solint.py (balík interpreter je relatívny k tomuto adresáru)
WORKDIR /app/src
ENTRYPOINT ["python", "solint.py"]


# ─────────────────────────────────────────
# Stage: test
# ─────────────────────────────────────────
FROM runtime AS test

# Node ako v stage build-test/check (predvolený balík z Debianu je zvyčajne starší)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_SETUP_MAJOR}.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /tester

# Skopíruj preložený tester z build-test stage
COPY --from=build-test /src/tester/dist ./dist
COPY --from=build-test /src/tester/node_modules ./node_modules
COPY --from=build-test /src/tester/package.json ./

ENTRYPOINT ["/bin/sh"]