# Image de l'application MiniShop (PHP) : FrankenPHP sert public/index.php sur le port 8000.

# --- Étape 1 : dépendances de production (sans les outils de test) ---
FROM docker.io/library/composer:2 AS vendor
WORKDIR /app
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-interaction --no-progress --prefer-dist --optimize-autoloader --ignore-platform-req=ext-apcu

# --- Étape 2 : image finale ---
FROM docker.io/dunglas/frankenphp:1-php8.4-alpine
# Correctifs de sécurité Alpine publiés depuis la construction de l'image de base (cf. Trivy, Atelier 11)
RUN apk upgrade --no-cache \
 && install-php-extensions apcu \
 && adduser -D -H appuser \
 # port 8000 : pas besoin du droit d'ouvrir un port privilégié
 && setcap -r /usr/local/bin/frankenphp \
 && chown -R appuser:appuser /config/caddy /data/caddy
COPY docker/php.ini /usr/local/etc/php/conf.d/minishop.ini
COPY docker/Caddyfile /etc/frankenphp/Caddyfile
WORKDIR /app
COPY --from=vendor /app/vendor ./vendor
COPY public ./public
COPY resources ./resources
COPY src ./src
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s CMD php -r "exit(false === @file_get_contents('http://localhost:8000/health') ? 1 : 0);"
