// Analyse de sécurité du code (SAST) — Atelier 11.
// Lancer :   npm run lint:security
import security from 'eslint-plugin-security';
import globals from 'globals';

export default [
  {
    files: ['src/**/*.js'],
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: 'module',
      globals: { ...globals.node },
    },
  },
  security.configs.recommended,
];
