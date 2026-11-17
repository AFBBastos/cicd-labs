<?php

declare(strict_types=1);

namespace MiniShop\BoiteNoire\E2e;

use PHPUnit\Framework\Attributes\Group;
use Symfony\Component\Panther\PantherTestCase;

/**
 * Test E2E Symfony Panther — POINT DE DÉPART (Atelier 8).
 *
 * Prérequis : application lancée (docker compose up -d --build dans declinaisons/php) ;
 * adresse lue dans MINISHOP_URL, http://localhost:8000 par défaut.
 * Lancer :   composer e2e                        (sans fenêtre)
 *            PANTHER_NO_HEADLESS=1 composer e2e  (pour voir le navigateur)
 * Navigateur : chrome par défaut ; MINISHOP_BROWSER=firefox pour Firefox.
 */
#[Group('e2e')]
final class ParcoursAchatTest extends PantherTestCase
{
    public function testPageAccueil(): void
    {
        $client = self::createPantherClient([
            'external_base_uri' => getenv('MINISHOP_URL') ?: 'http://localhost:8000',
            'browser' => getenv('MINISHOP_BROWSER') ?: self::CHROME,
        ]);
        $client->request('GET', '/');

        self::assertStringContainsString('MiniShop', $client->getTitle());
        // Les produits sont chargés en JavaScript : on attend le dernier, sans sleep().
        $crawler = $client->waitFor('[data-testid="products"] li:nth-child(5)');
        self::assertCount(5, $crawler->filter('[data-testid="products"] li'));
    }

    // TODO Atelier 8 : ajouter 2 mugs, appliquer WELCOME10, vérifier le total, commander.
}
