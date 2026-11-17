<?php

declare(strict_types=1);

namespace MiniShop\Http;

use Psr\Http\Message\ResponseInterface;
use Psr\Http\Message\ServerRequestInterface;
use Psr\Http\Server\MiddlewareInterface;
use Psr\Http\Server\RequestHandlerInterface;
use Slim\Interfaces\RouteResolverInterface;
use Slim\Routing\RoutingResults;

/**
 * Observe chaque requête : métriques Prometheus, ligne de log JSON et bug injectable « slow ».
 *
 * L'étiquette « path » des métriques est le gabarit de la route (/products/{product_id}), pas l'URL
 * réelle : sinon chaque identifiant créerait une série différente. Une URL sans route reçoit une
 * étiquette fixe, pour qu'un scanner ne crée pas une série Prometheus par URL demandée ; le journal,
 * lui, garde le chemin réel (repérage des scans).
 */
final readonly class ObserveMiddleware implements MiddlewareInterface
{
    public const string UNKNOWN_ROUTE = '(route inconnue)';

    public function __construct(
        private RouteResolverInterface $routes,
        private Metrics $metrics,
        private ?string $logFile,
    ) {
    }

    public function process(ServerRequestInterface $request, RequestHandlerInterface $handler): ResponseInterface
    {
        $start = hrtime(true);
        $urlPath = $request->getUri()->getPath();
        // Bug injectable pour les démos de performance (MINISHOP_BUG=slow)
        if ('slow' === getenv('MINISHOP_BUG') && str_starts_with($urlPath, '/cart')) {
            // Seule la requête en cours attend : FrankenPHP traite chaque requête dans son propre fil.
            usleep(random_int(300_000, 800_000));
        }

        $response = $handler->handle($request);

        $elapsed = (hrtime(true) - $start) / 1e9;
        $pattern = $this->routePattern($request->getMethod(), $urlPath);
        $label = $pattern ?? self::UNKNOWN_ROUTE;
        $this->metrics->observeRequest($request->getMethod(), $label, $response->getStatusCode(), $elapsed);
        $this->log([
            'ts' => microtime(true),
            'method' => $request->getMethod(),
            'path' => $pattern ?? mb_scrub($urlPath, 'UTF-8'),
            'status' => $response->getStatusCode(),
            'latency_ms' => round($elapsed * 1000, 2),
        ]);

        return $response;
    }

    /** Gabarit de la route qui sert l'URL, ou null (route inconnue, méthode refusée). */
    private function routePattern(string $method, string $urlPath): ?string
    {
        $results = $this->routes->computeRoutingResults($urlPath, $method);
        $identifier = $results->getRouteIdentifier();
        if (RoutingResults::FOUND !== $results->getRouteStatus() || null === $identifier) {
            return null;
        }
        $pattern = $this->routes->resolveRoute($identifier)->getPattern();

        return str_starts_with($pattern, '/static/') ? '/static' : $pattern;
    }

    /** @param array<string, mixed> $entry */
    private function log(array $entry): void
    {
        if (null === $this->logFile) {
            return;
        }
        $directory = \dirname($this->logFile);
        if (!is_dir($directory)) {
            @mkdir($directory, 0o777, true);
        }
        file_put_contents($this->logFile, json_encode($entry, \JSON_UNESCAPED_SLASHES)."\n", \FILE_APPEND | \LOCK_EX);
    }
}
