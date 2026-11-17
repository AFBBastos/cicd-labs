/**
 * API HTTP MiniShop (Fastify).
 *
 * Lancer :  npm start            (ou : npm run dev, qui redémarre à chaque sauvegarde)
 * Docs   :  http://localhost:8000/docs   (OpenAPI : /openapi.json)
 *
 * buildApp() construit l'application sans ouvrir de port : les tests l'appellent
 * « en mémoire » avec app.inject(). Le serveur réel est démarré par src/server.js.
 */

import { randomUUID } from 'node:crypto';
import { createWriteStream, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { setTimeout as sleep } from 'node:timers/promises';
import { fileURLToPath } from 'node:url';

import fastifyStatic from '@fastify/static';
import fastifySwagger from '@fastify/swagger';
import fastifySwaggerUi from '@fastify/swagger-ui';
import Fastify from 'fastify';
import { Counter, Histogram, Registry } from 'prom-client';

import { UnknownProductError, getProduct, listProducts } from './catalog.js';
import { quote } from './pricing.js';

export const VERSION = '1.0.0';

const STATIC_DIR = join(dirname(fileURLToPath(import.meta.url)), 'static');

// ---------------------------------------------------------------- schémas JSON (validation + OpenAPI)
const ITEM_SCHEMA = {
  $id: 'Item',
  type: 'object',
  required: ['product_id', 'qty'],
  properties: {
    product_id: { type: 'string', examples: ['mug'] },
    qty: { type: 'integer', minimum: 1, maximum: 99, examples: [2] },
  },
};

const CART_SCHEMA = {
  $id: 'Cart',
  type: 'object',
  properties: {
    items: { type: 'array', items: { $ref: 'Item#' }, default: [] },
    coupon: { type: ['string', 'null'], default: null, examples: ['WELCOME10'] },
  },
};

const PRODUCT_SCHEMA = {
  $id: 'Product',
  type: 'object',
  required: ['id', 'name', 'price', 'stock'],
  properties: {
    id: { type: 'string' },
    name: { type: 'string' },
    price: { type: 'string', description: 'Prix TTC en euros, 2 décimales', examples: ['12.50'] },
    stock: { type: 'integer' },
  },
};

const QUOTE_PROPERTIES = {
  lines: {
    type: 'array',
    items: {
      type: 'object',
      required: ['product_id', 'qty', 'unit_price', 'total'],
      properties: {
        product_id: { type: 'string' },
        qty: { type: 'integer' },
        unit_price: { type: 'string' },
        total: { type: 'string' },
      },
    },
  },
  subtotal: { type: 'string' },
  discount: { type: 'string' },
  shipping: { type: 'string' },
  total: { type: 'string' },
  coupon: { type: ['string', 'null'] },
};
const QUOTE_FIELDS = Object.keys(QUOTE_PROPERTIES);

const QUOTE_SCHEMA = {
  $id: 'Quote',
  type: 'object',
  required: QUOTE_FIELDS,
  properties: QUOTE_PROPERTIES,
};

const ORDER_SCHEMA = {
  $id: 'Order',
  type: 'object',
  required: ['id', ...QUOTE_FIELDS],
  properties: { id: { type: 'string', examples: ['a1b2c3d4e5f6'] }, ...QUOTE_PROPERTIES },
};

const ERROR_SCHEMA = {
  $id: 'Error',
  type: 'object',
  required: ['detail'],
  properties: { detail: { type: 'string' } },
};

const VALIDATION_ERROR_SCHEMA = {
  $id: 'ValidationError',
  type: 'object',
  required: ['detail'],
  properties: {
    detail: {
      description: 'Message (erreur métier) ou liste des erreurs de validation du corps',
      anyOf: [
        { type: 'string' },
        {
          type: 'array',
          items: {
            type: 'object',
            properties: { loc: { type: 'string' }, msg: { type: 'string' } },
          },
        },
      ],
    },
  },
};

const SCHEMAS = [
  ITEM_SCHEMA,
  CART_SCHEMA,
  PRODUCT_SCHEMA,
  QUOTE_SCHEMA,
  ORDER_SCHEMA,
  ERROR_SCHEMA,
  VALIDATION_ERROR_SCHEMA,
];

/** Erreur HTTP portant le champ `detail` renvoyé au client. */
class HttpError extends Error {
  /**
   * @param {number} statusCode
   * @param {string} detail
   */
  constructor(statusCode, detail) {
    super(detail);
    this.statusCode = statusCode;
    this.detail = detail;
  }
}

/** @param {import('./catalog.js').Product} product */
function productToJSON(product) {
  return {
    id: product.id,
    name: product.name,
    price: product.price.toFixed(2),
    stock: product.stock,
  };
}

/**
 * Calcule le devis d'un panier et traduit les erreurs métier en erreurs HTTP.
 *
 * @param {{ items: import('./pricing.js').Item[], coupon: string | null }} cart
 */
function quoteCart(cart) {
  try {
    return quote(cart.items, cart.coupon);
  } catch (error) {
    if (error instanceof UnknownProductError) {
      throw new HttpError(404, error.message);
    }
    if (error instanceof RangeError || error instanceof TypeError) {
      throw new HttpError(422, error.message);
    }
    throw error;
  }
}

/** Étiquette `path` des métriques quand aucune route ne correspond à l'URL demandée. */
const UNKNOWN_ROUTE = '(route inconnue)';

/**
 * Gabarit de la route (« /products/{product_id} ») plutôt que l'URL réelle ; null si aucune route
 * déclarée ne correspond (404, 405) ou s'il s'agit d'un fichier (statique, documentation).
 *
 * @param {import('fastify').FastifyRequest} request
 * @returns {string | null}
 */
function routeTemplate(request) {
  const route = request.routeOptions.url;
  if (!route || route.includes('*')) {
    return null;
  }
  return route.replace(/:(\w+)/g, '{$1}');
}

/**
 * Construit l'application.
 *
 * @param {{ logFile?: string }} [options] logFile : journal JSON des requêtes
 *   (défaut : variable d'environnement MINISHOP_LOG_FILE ; absent = pas de journal).
 * @returns {Promise<import('fastify').FastifyInstance>}
 */
export async function buildApp(options = {}) {
  const app = Fastify({
    logger: false,
    ajv: {
      customOptions: {
        // Types JSON stricts, comme dans le contrat OpenAPI : "2" n'est pas un entier, 5 n'est pas une chaîne.
        coerceTypes: false,
        // « examples » n'est pas un mot-clé de validation : on le garde pour la documentation.
        strict: false,
      },
    },
  });

  // ---------------------------------------------------------------- métriques et journal
  const registry = new Registry();
  const requests = new Counter({
    name: 'minishop_http_requests_total',
    help: 'Requêtes HTTP',
    labelNames: ['method', 'path', 'status'],
    registers: [registry],
  });
  const latency = new Histogram({
    name: 'minishop_http_request_duration_seconds',
    help: 'Latence HTTP',
    labelNames: ['path'],
    buckets: [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10],
    registers: [registry],
  });
  const ordersCreated = new Counter({
    name: 'minishop_orders_total',
    help: 'Commandes créées',
    registers: [registry],
  });

  const logFile = options.logFile ?? process.env.MINISHOP_LOG_FILE; // ex. logs/app.jsonl
  let logStream = null;
  if (logFile) {
    // Le chemin vient de l'exploitant (variable d'environnement), jamais d'un client de l'API :
    // l'alerte du SAST est examinée puis levée, avec sa justification (Atelier 11).
    // eslint-disable-next-line security/detect-non-literal-fs-filename -- chemin de l'exploitant
    mkdirSync(dirname(logFile), { recursive: true });
    // eslint-disable-next-line security/detect-non-literal-fs-filename -- chemin de l'exploitant
    logStream = createWriteStream(logFile, { flags: 'a' });
    app.addHook('onClose', () => new Promise((resolve) => logStream.end(resolve)));
  }

  app.addHook('onRequest', async (request) => {
    // Bug injectable pour les démos de performance (MINISHOP_BUG=slow)
    if (process.env.MINISHOP_BUG === 'slow' && request.url.startsWith('/cart')) {
      await sleep(300 + Math.random() * 500);
    }
  });

  app.addHook('onResponse', async (request, reply) => {
    const template = routeTemplate(request);
    const path = template ?? request.url.split('?')[0]; // chemin réel dans le journal (repérage des scans)
    // Étiquette de métrique : le gabarit de la route ; à défaut le chemin d'une ressource servie
    // (fichier statique, /docs) ; sinon une valeur fixe (404, 405…), pour qu'un scanner ne crée pas
    // une nouvelle série Prometheus par URL demandée.
    const served = reply.statusCode === 200 || reply.statusCode === 304;
    const label = template ?? (served ? path : UNKNOWN_ROUTE);
    const elapsedMs = reply.elapsedTime;
    requests.inc({ method: request.method, path: label, status: reply.statusCode });
    latency.observe({ path: label }, elapsedMs / 1000);
    logStream?.write(
      `${JSON.stringify({
        ts: Date.now() / 1000,
        method: request.method,
        path,
        status: reply.statusCode,
        latency_ms: Math.round(elapsedMs * 100) / 100,
      })}\n`,
    );
  });

  // ---------------------------------------------------------------- erreurs : toujours { detail }
  app.setErrorHandler((error, request, reply) => {
    if (error instanceof HttpError) {
      return reply.code(error.statusCode).send({ detail: error.detail });
    }
    if (error.validation) {
      const detail = error.validation.map((issue) => ({
        loc: `${error.validationContext}${issue.instancePath}`,
        msg: issue.message,
      }));
      return reply.code(422).send({ detail });
    }
    if (error.statusCode === 400 || error.statusCode === 415) {
      // Corps illisible (JSON mal formé, type de contenu inattendu) : même code que la validation.
      return reply.code(422).send({ detail: error.message });
    }
    if (error.statusCode && error.statusCode < 500) {
      return reply.code(error.statusCode).send({ detail: error.message });
    }
    return reply.code(500).send({ detail: 'Internal Server Error' });
  });

  // Une URL connue appelée avec une autre méthode répond 405 (et non 404), avec l'en-tête Allow.
  /** @type {{ method: string, pattern: RegExp }[]} */
  const knownRoutes = [];
  app.addHook('onRoute', (route) => {
    if (route.url.includes('*')) {
      return; // fichiers statiques et pages de documentation
    }
    const source = route.url.replace(/:\w+/g, '[^/]+');
    // eslint-disable-next-line security/detect-non-literal-regexp -- gabarits de nos propres routes
    const pattern = new RegExp(`^${source}$`);
    for (const method of [route.method].flat()) {
      knownRoutes.push({ method, pattern });
    }
  });

  const notFoundOrNotAllowed = (request, reply) => {
    const path = request.url.split('?')[0];
    const allowed = knownRoutes.filter((route) => route.pattern.test(path)).map((r) => r.method);
    if (allowed.length > 0) {
      return reply
        .code(405)
        .header('Allow', [...new Set(allowed)].join(', '))
        .send({ detail: 'Method Not Allowed' });
    }
    return reply.code(404).send({ detail: 'Not Found' });
  };
  app.setNotFoundHandler(notFoundOrNotAllowed);

  // Méthodes que l'API n'utilise jamais (PUT, QUERY…) : refusées avant toute lecture du corps.
  app.addHook('onRequest', async (request, reply) => {
    if (!['GET', 'HEAD', 'POST', 'OPTIONS'].includes(request.method)) {
      return notFoundOrNotAllowed(request, reply);
    }
  });

  // ---------------------------------------------------------------- documentation OpenAPI
  for (const schema of SCHEMAS) {
    app.addSchema(schema);
  }
  await app.register(fastifySwagger, {
    openapi: {
      openapi: '3.0.3',
      info: {
        title: 'MiniShop',
        version: VERSION,
        description: 'Application fil rouge de la formation CI/CD & IA',
      },
    },
    refResolver: { buildLocalReference: (json) => json.$id },
  });
  await app.register(fastifySwaggerUi, { routePrefix: '/docs' });
  app.get('/openapi.json', { schema: { hide: true } }, async () => app.swagger());

  // ---------------------------------------------------------------- page web et fichiers statiques
  await app.register(fastifyStatic, { root: STATIC_DIR, prefix: '/static/', schemaHide: true });
  app.get('/', { schema: { hide: true } }, (request, reply) => reply.sendFile('index.html'));

  // ---------------------------------------------------------------- routes
  app.get(
    '/health',
    {
      schema: {
        summary: 'Health',
        response: {
          200: {
            type: 'object',
            required: ['status', 'version'],
            properties: { status: { type: 'string' }, version: { type: 'string' } },
          },
        },
      },
    },
    async () => ({ status: 'ok', version: VERSION }),
  );

  app.get('/metrics', { schema: { hide: true } }, async (request, reply) => {
    reply.type(registry.contentType);
    return registry.metrics();
  });

  app.get(
    '/products',
    {
      schema: {
        summary: 'Products',
        response: { 200: { type: 'array', items: { $ref: 'Product#' } } },
      },
    },
    async () => listProducts().map(productToJSON),
  );

  app.get(
    '/products/:product_id',
    {
      schema: {
        summary: 'Product',
        params: {
          type: 'object',
          required: ['product_id'],
          properties: { product_id: { type: 'string' } },
        },
        response: { 200: { $ref: 'Product#' }, 404: { $ref: 'Error#' } },
      },
    },
    async (request) => {
      try {
        return productToJSON(getProduct(request.params.product_id));
      } catch (error) {
        if (error instanceof UnknownProductError) {
          throw new HttpError(404, error.message);
        }
        throw error;
      }
    },
  );

  app.post(
    '/cart/quote',
    {
      schema: {
        summary: 'Cart Quote',
        body: { $ref: 'Cart#' },
        response: {
          200: { $ref: 'Quote#' },
          404: { $ref: 'Error#' },
          422: { $ref: 'ValidationError#' },
        },
      },
    },
    async (request) => quoteCart(request.body).toJSON(),
  );

  /** @type {Map<string, object>} Commandes en mémoire (perdues au redémarrage). */
  const orders = new Map();

  app.post(
    '/orders',
    {
      schema: {
        summary: 'Create Order',
        body: { $ref: 'Cart#' },
        response: {
          201: { $ref: 'Order#' },
          404: { $ref: 'Error#' },
          422: { $ref: 'ValidationError#' },
        },
      },
    },
    async (request, reply) => {
      if (request.body.items.length === 0) {
        throw new HttpError(422, 'Panier vide');
      }
      const q = quoteCart(request.body);
      const id = randomUUID().replaceAll('-', '').slice(0, 12);
      const order = { id, ...q.toJSON() };
      orders.set(id, order);
      ordersCreated.inc();
      reply.code(201);
      return order;
    },
  );

  app.get(
    '/orders/:order_id',
    {
      schema: {
        summary: 'Get Order',
        params: {
          type: 'object',
          required: ['order_id'],
          properties: { order_id: { type: 'string' } },
        },
        response: { 200: { $ref: 'Order#' }, 404: { $ref: 'Error#' } },
      },
    },
    async (request) => {
      const order = orders.get(request.params.order_id);
      if (order === undefined) {
        throw new HttpError(404, 'Commande introuvable');
      }
      return order;
    },
  );

  return app;
}
