import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: 'e2e',
  reporter: 'list',
  use: {
    // Adresse de l'application (lancée avec Docker à la racine du dépôt).
    baseURL: process.env.MINISHOP_URL ?? 'http://localhost:8000',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  ],
});
