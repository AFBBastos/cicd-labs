FROM node:22-slim
WORKDIR /app
# Correctifs de sécurité Debian publiés depuis la construction de l'image de base (cf. Trivy, Atelier 11)
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
COPY package.json package-lock.json ./
# Dépendances de production seulement, versions figées par package-lock.json
RUN npm ci --omit=dev && npm cache clean --force \
    # npm, corepack et yarn ne servent plus après l'installation : les retirer réduit la surface d'attaque
    # (leurs propres dépendances sont régulièrement signalées par Trivy)
    && rm -rf /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/corepack /opt/yarn-* \
       /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack /usr/local/bin/yarn /usr/local/bin/yarnpkg
COPY src ./src
ENV NODE_ENV=production
# Utilisateur non root fourni par l'image officielle
USER node
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s CMD node -e "fetch('http://localhost:8000/health').then((r) => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"
CMD ["node", "src/server.js"]
