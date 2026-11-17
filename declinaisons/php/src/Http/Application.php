<?php

declare(strict_types=1);

namespace MiniShop\Http;

use MiniShop\Catalog;
use MiniShop\Pricing;
use MiniShop\Product;
use MiniShop\Quote;
use MiniShop\UnknownProductException;
use Prometheus\Storage\APCng;
use Psr\Container\ContainerInterface;
use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\App;
use Slim\Exception\HttpException;
use Slim\Exception\HttpMethodNotAllowedException;
use Slim\Exception\HttpNotFoundException;
use Slim\Factory\AppFactory;
use Slim\Psr7\Factory\ResponseFactory;

/**
 * API HTTP MiniShop (Slim 4).
 *
 * Lancer : docker compose up -d --build     (ou : composer serve)
 * Docs   : http://localhost:8000/docs        (OpenAPI : /openapi.json)
 *
 * Même contrat que la version Python (minishop/api.py) : routes, codes, corps JSON, métriques, logs.
 */
final class Application
{
    public const string VERSION = '1.0.0';

    private const string RESOURCES = __DIR__.'/../../resources';

    /**
     * Construit l'application. Sans argument, l'état (commandes, métriques) vit dans APCu si
     * l'extension est active, sinon dans la mémoire du processus — ce qui suffit aux tests.
     *
     * @return App<ContainerInterface|null>
     */
    public static function create(?OrderRepository $orders = null, ?Metrics $metrics = null): App
    {
        $shared = \function_exists('apcu_enabled') && apcu_enabled();
        $orders ??= $shared ? new ApcuOrderRepository() : new InMemoryOrderRepository();
        $metrics ??= new Metrics($shared ? new APCng(decimalPrecision: 6) : null);

        $app = AppFactory::create(new ResponseFactory());
        self::routes($app, $orders, $metrics);

        // Les middlewares s'empilent : le dernier ajouté est le premier exécuté.
        $app->addRoutingMiddleware();
        $app->addErrorMiddleware(false, false, false)->setDefaultErrorHandler(
            static fn (Request $request, \Throwable $error): Response => self::error($error),
        );
        $logFile = getenv('MINISHOP_LOG_FILE');
        $app->add(new ObserveMiddleware(
            $app->getRouteResolver(),
            $metrics,
            false === $logFile || '' === $logFile ? null : $logFile,
        ));

        return $app;
    }

    /** @param App<ContainerInterface|null> $app */
    private static function routes(App $app, OrderRepository $orders, Metrics $metrics): void
    {
        $app->get('/', static fn (Request $request, Response $response): Response => self::file(
            $response,
            self::RESOURCES.'/static/index.html',
            'text/html; charset=utf-8',
        ));

        $app->get('/static/{file}', static function (Request $request, Response $response, array $args): Response {
            // On ne sert que les fichiers réellement présents dans le dossier : pas de chemin construit
            // à partir de l'URL, donc pas de sortie du dossier possible (« ../ »).
            foreach (scandir(self::RESOURCES.'/static') ?: [] as $name) {
                if ($name === $args['file'] && is_file(self::RESOURCES.'/static/'.$name)) {
                    $type = str_ends_with($name, '.css') ? 'text/css; charset=utf-8' : 'text/html; charset=utf-8';

                    return self::file($response, self::RESOURCES.'/static/'.$name, $type);
                }
            }

            return self::json($response, ['detail' => 'Not Found'], 404);
        });

        $app->get('/health', static fn (Request $request, Response $response): Response => self::json(
            $response,
            ['status' => 'ok', 'version' => self::VERSION],
        ));

        $app->get('/metrics', static function (Request $request, Response $response) use ($metrics): Response {
            $response->getBody()->write($metrics->render());

            return $response->withHeader('Content-Type', Metrics::CONTENT_TYPE);
        });

        $app->get('/openapi.json', static fn (Request $request, Response $response): Response => self::file(
            $response,
            self::RESOURCES.'/openapi.json',
            'application/json',
        ));

        $app->get('/docs', static fn (Request $request, Response $response): Response => self::file(
            $response,
            self::RESOURCES.'/docs.html',
            'text/html; charset=utf-8',
        ));

        $app->get('/products', static fn (Request $request, Response $response): Response => self::json(
            $response,
            array_map(self::product(...), Catalog::listProducts()),
        ));

        $app->get('/products/{product_id}', static function (Request $request, Response $response, array $args): Response {
            try {
                return self::json($response, self::product(Catalog::getProduct($args['product_id'])));
            } catch (UnknownProductException $exception) {
                return self::json($response, ['detail' => $exception->getMessage()], 404);
            }
        });

        $app->post('/cart/quote', static function (Request $request, Response $response): Response {
            $quote = self::quote(CartRequest::fromJson((string) $request->getBody()));

            return $quote instanceof Quote ? self::json($response, $quote->toArray()) : $quote;
        });

        $app->post('/orders', static function (Request $request, Response $response) use ($orders, $metrics): Response {
            $cart = CartRequest::fromJson((string) $request->getBody());
            if ([] === $cart->errors && [] === $cart->items) {
                return self::json($response, ['detail' => 'Panier vide'], 422);
            }
            $quote = self::quote($cart);
            if (!$quote instanceof Quote) {
                return $quote;
            }
            $id = bin2hex(random_bytes(6));
            $order = ['id' => $id, ...$quote->toArray()];
            $orders->save($id, $order);
            $metrics->orderCreated();

            return self::json($response, $order, 201);
        });

        $app->get('/orders/{order_id}', static function (Request $request, Response $response, array $args) use ($orders): Response {
            $order = $orders->find($args['order_id']);

            return null === $order
                ? self::json($response, ['detail' => 'Commande introuvable'], 404)
                : self::json($response, $order);
        });
    }

    /** Devis du panier, ou réponse d'erreur (422 corps ou règle métier, 404 produit inconnu). */
    private static function quote(CartRequest $cart): Quote|Response
    {
        $response = (new ResponseFactory())->createResponse();
        if ([] !== $cart->errors) {
            return self::json($response, ['detail' => $cart->errors], 422);
        }
        try {
            return Pricing::quote($cart->items, $cart->coupon);
        } catch (UnknownProductException $exception) {
            return self::json($response, ['detail' => $exception->getMessage()], 404);
        } catch (\InvalidArgumentException $exception) {
            return self::json($response, ['detail' => $exception->getMessage()], 422);
        }
    }

    /** @return array{id: string, name: string, price: string, stock: int} */
    private static function product(Product $product): array
    {
        return [
            'id' => $product->id,
            'name' => $product->name,
            'price' => (string) $product->price,
            'stock' => $product->stock,
        ];
    }

    /** Route inconnue, méthode refusée ou erreur imprévue : même forme que les autres erreurs. */
    private static function error(\Throwable $error): Response
    {
        $response = (new ResponseFactory())->createResponse();
        if ($error instanceof HttpMethodNotAllowedException) {
            $response = $response->withHeader('Allow', implode(', ', $error->getAllowedMethods()));

            return self::json($response, ['detail' => 'Method Not Allowed'], 405);
        }
        if ($error instanceof HttpNotFoundException) {
            return self::json($response, ['detail' => 'Not Found'], 404);
        }
        if ($error instanceof HttpException) {
            return self::json($response, ['detail' => $error->getMessage()], $error->getCode());
        }

        return self::json($response, ['detail' => 'Internal Server Error'], 500);
    }

    private static function json(Response $response, mixed $data, int $status = 200): Response
    {
        $flags = \JSON_UNESCAPED_UNICODE | \JSON_UNESCAPED_SLASHES | \JSON_INVALID_UTF8_SUBSTITUTE
            | \JSON_PRESERVE_ZERO_FRACTION | \JSON_THROW_ON_ERROR;
        $response->getBody()->write(json_encode($data, $flags));

        return $response->withStatus($status)->withHeader('Content-Type', 'application/json');
    }

    private static function file(Response $response, string $path, string $contentType): Response
    {
        $response->getBody()->write((string) file_get_contents($path));

        return $response->withHeader('Content-Type', $contentType);
    }
}
