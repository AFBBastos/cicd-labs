import js from '@eslint/js';
import security from 'eslint-plugin-security';
import globals from 'globals';

export default [
  { ignores: ['coverage/', 'reports/', 'node_modules/', '.stryker-tmp/', 'test-results/'] },
  js.configs.recommended,
  {
    // Le greffon de sécurité est seulement déclaré ici (ses règles tournent avec npm run lint:security) :
    // cela permet aux commentaires « eslint-disable security/… » du code d'être reconnus.
    plugins: { security },
    linterOptions: { reportUnusedDisableDirectives: 'off' },
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: 'module',
      globals: { ...globals.node },
    },
    rules: {
      eqeqeq: 'error',
      'no-var': 'error',
      'prefer-const': 'error',
    },
  },
];
