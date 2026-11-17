<?php

declare(strict_types=1);

namespace MiniShop\Tests\Api;

use PHPUnit\Framework\Attributes\Group;

/** Tests d'API en mémoire — POINT DE DÉPART (Atelier 9). */
#[Group('api')]
final class ApiSmokeTest extends ApiTestCase
{
    public function testHealth(): void
    {
        $response = $this->get('/health');

        self::assertSame(200, $response->getStatusCode());
        self::assertSame('ok', self::json($response)['status']);
    }

    public function testListeProduits(): void
    {
        $response = $this->get('/products');

        self::assertSame(200, $response->getStatusCode());
        $ids = array_column(self::json($response), 'id');
        self::assertContains('mug', $ids);
        self::assertContains('tshirt', $ids);
    }

    // TODO Atelier 9 : /products/{id} (200, 404), /cart/quote (200, 404, 422), /orders (201, 422), GET /orders/{id}
}
