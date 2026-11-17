import { configDefaults, defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['**/*.test.js'],
    exclude: [...configDefaults.exclude, '.stryker-tmp/**'],
    // Les variables d'environnement modifiées par vi.stubEnv() sont restaurées après chaque test.
    unstubEnvs: true,
    coverage: {
      provider: 'v8',
      include: ['src/**/*.js'],
      // text : tableau dans le terminal et dans coverage/coverage.txt ; html : coverage/index.html ;
      // cobertura : coverage/cobertura-coverage.xml (format lu par les outils de CI)
      reporter: [
        ['text', { skipFull: false }],
        ['text', { file: 'coverage.txt' }],
        'html',
        'cobertura',
      ],
      reportsDirectory: 'coverage',
    },
  },
});
