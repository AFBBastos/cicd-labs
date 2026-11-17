/**
 * Tests d'API — POINT DE DÉPART (Atelier 9).
 *
 * Prérequis : application lancée (docker compose up -d --build à la racine du dépôt) ;
 * MINISHOP_URL=http://localhost:8000 par défaut.
 * Lancer :   npm run test:api
 */

import { describe, expect, test } from 'vitest';

// Ne pas nommer cette variable d'environnement BASE_URL : Vitest la réserve (valeur « / »).
const APP_URL = process.env.MINISHOP_URL ?? 'http://localhost:8000';

describe('api', () => {
  test('GET /health', async () => {
    const res = await fetch(`${APP_URL}/health`);

    expect(res.status).toBe(200);
    expect((await res.json()).status).toBe('ok');
  });

  test('GET /products : liste des produits', async () => {
    const res = await fetch(`${APP_URL}/products`);

    expect(res.status).toBe(200);
    const ids = (await res.json()).map((product) => product.id);
    expect(ids).toEqual(expect.arrayContaining(['mug', 'tshirt']));
  });
});

// TODO Atelier 9 : /products/{id} (200, 404), /cart/quote (200, 404, 422), /orders (201, 422), GET /orders/{id}
