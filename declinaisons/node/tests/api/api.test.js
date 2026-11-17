/**
 * Tests d'API « en mémoire » — POINT DE DÉPART (Atelier 2, puis Atelier 9).
 *
 * app.inject() appelle l'application sans ouvrir de port : rapide, pas de serveur à lancer.
 * Lancer :   npm run test:api
 */

import { afterAll, beforeAll, describe, expect, test } from 'vitest';

import { buildApp } from '../../src/app.js';

describe('api', () => {
  /** @type {import('fastify').FastifyInstance} */
  let app;

  beforeAll(async () => {
    app = await buildApp();
  });

  afterAll(async () => {
    await app.close();
  });

  test('GET /health', async () => {
    const res = await app.inject({ method: 'GET', url: '/health' });

    expect(res.statusCode).toBe(200);
    expect(res.json().status).toBe('ok');
  });

  test('GET /products : liste des produits', async () => {
    const res = await app.inject({ method: 'GET', url: '/products' });

    expect(res.statusCode).toBe(200);
    const ids = res.json().map((product) => product.id);
    expect(ids).toEqual(expect.arrayContaining(['mug', 'tshirt']));
  });
});

// TODO Atelier 9 : /products/{id} (200, 404), /cart/quote (200, 404, 422), /orders (201, 422), GET /orders/{id}
