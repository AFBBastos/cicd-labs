<?php

declare(strict_types=1);

namespace MiniShop\BoiteNoire\Api;

use GuzzleHttp\Client;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\TestCase;

/**
 * Tests d'API — POINT DE DÉPART (Atelier 9).
 *
 * Prérequis : application lancée (docker compose up -d --build dans declinaisons/php).
 * Adresse lue dans MINISHOP_URL, http://localhost:8000 par défaut.
 */
#[Group('api')]
final class ApiSmokeTest extends TestCase
{
    private Client $http;

    protected function setUp(): void
    {
        $this->http = new Client([
            'base_uri' => getenv('MINISHOP_URL') ?: 'http://localhost:8000',
            'http_errors' => false, // un 404 ou un 422 est une réponse à vérifier, pas une exception
            'timeout' => 5,
        ]);
    }

    public function testHealth(): void
    {
        $response = $this->http->get('/health');

        self::assertSame(200, $response->getStatusCode());
        self::assertSame('ok', $this->json((string) $response->getBody())['status']);
    }

    public function testListeProduits(): void
    {
        $response = $this->http->get('/products');

        self::assertSame(200, $response->getStatusCode());
        $ids = array_column($this->json((string) $response->getBody()), 'id');
        self::assertContains('mug', $ids);
        self::assertContains('tshirt', $ids);
    }

    // TODO Atelier 9 : /products/{id} (200, 404), /cart/quote (200, 404, 422), /orders (201, 422), GET /orders/{id}

    /** @return array<mixed> */
    private function json(string $body): array
    {
        return json_decode($body, true, flags: \JSON_THROW_ON_ERROR);
    }
}
