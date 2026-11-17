/**
 * Test E2E Playwright — POINT DE DÉPART (Atelier 8).
 *
 * Prérequis : application lancée (docker compose up -d --build à la racine du dépôt) ;
 * MINISHOP_URL=http://localhost:8000 par défaut.
 * Lancer :   npx playwright test --project=chromium --headed        (pour voir le navigateur)
 */

import { expect, test } from '@playwright/test';

test("page d'accueil", async ({ page }) => {
  await page.goto('/');

  await expect(page).toHaveTitle(/MiniShop/);
  await expect(page.getByTestId('products').locator('li')).toHaveCount(5);
});

// TODO Atelier 8 : ajouter 2 mugs, appliquer WELCOME10, vérifier le total, commander.
