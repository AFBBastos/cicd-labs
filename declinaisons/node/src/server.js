/**
 * Point d'entrée du serveur MiniShop : écoute sur le port 8000, toutes interfaces.
 *
 * Lancer :  npm start        (variables : PORT, MINISHOP_BUG, MINISHOP_LOG_FILE)
 */

import { buildApp } from './app.js';

const port = Number(process.env.PORT ?? 8000);
const app = await buildApp();

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, async () => {
    await app.close();
    process.exit(0);
  });
}

try {
  await app.listen({ host: '0.0.0.0', port });
  console.log(`MiniShop écoute sur http://localhost:${port}  (documentation : /docs)`);
} catch (error) {
  console.error(error);
  process.exit(1);
}
