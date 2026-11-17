<?php

declare(strict_types=1);

namespace MiniShop\Tests\Api;

use MiniShop\Http\Application;
use PHPUnit\Framework\TestCase;
use Psr\Container\ContainerInterface;
use Psr\Http\Message\ResponseInterface;
use Slim\App;
use Slim\Psr7\Factory\ServerRequestFactory;

/**
 * Client HTTP « en mémoire » : les requêtes sont passées directement à l'application,
 * sans serveur à lancer (équivalent du TestClient de la version Python).
 *
 * Chaque test reçoit une application neuve : commandes et métriques repartent de zéro.
 */
abstract class ApiTestCase extends TestCase
{
    /** @var App<ContainerInterface|null> */
    private App $app;

    protected function setUp(): void
    {
        $this->app = Application::create();
    }

    protected function get(string $path): ResponseInterface
    {
        return $this->app->handle((new ServerRequestFactory())->createServerRequest('GET', $path));
    }

    /** Envoie $payload en JSON (une chaîne est envoyée telle quelle, pour tester un corps invalide). */
    protected function post(string $path, mixed $payload): ResponseInterface
    {
        $request = (new ServerRequestFactory())->createServerRequest('POST', $path)
            ->withHeader('Content-Type', 'application/json');
        $request->getBody()->write(\is_string($payload) ? $payload : json_encode($payload, \JSON_THROW_ON_ERROR));

        return $this->app->handle($request);
    }

    /** Corps JSON décodé de la réponse. */
    protected static function json(ResponseInterface $response): mixed
    {
        return json_decode((string) $response->getBody(), true, flags: \JSON_THROW_ON_ERROR);
    }
}
