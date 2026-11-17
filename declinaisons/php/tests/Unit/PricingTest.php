<?php

declare(strict_types=1);

namespace MiniShop\Tests\Unit;

use Brick\Math\BigDecimal;
use MiniShop\Pricing;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\TestCase;

/**
 * Tests unitaires des règles de prix — POINT DE DÉPART (Atelier 1).
 *
 * Complétez ce fichier : objectif >= 90 % de couverture sur src/Pricing.php.
 *
 * Les montants se comparent sous forme de chaîne : (string) BigDecimal donne « 0.13 »,
 * ce qui vérifie à la fois la valeur et les deux décimales.
 */
#[Group('unit')]
final class PricingTest extends TestCase
{
    /** 0.125 s'arrondit à 0.13 (arrondi commercial HALF_UP), pas 0.12. */
    public function testMoneyArrondiCommercial(): void
    {
        self::assertSame('0.13', (string) Pricing::money('0.125'));
    }

    public function testLineTotalSansRemise(): void
    {
        self::assertSame('25.00', (string) Pricing::lineTotal(BigDecimal::of('12.50'), 2));
    }

    /** Un panier vide coûte 0 € : pas de frais de livraison. */
    public function testQuotePanierVide(): void
    {
        $quote = Pricing::quote([]);

        self::assertSame('0.00', (string) $quote->total);
        self::assertSame('0.00', (string) $quote->shipping);
    }

    // TODO Atelier 1 :
    //  - remise volume à partir de 10 unités (et pas à 9 !)
    //  - quantités invalides (0, 100, -1, "2", true) -> InvalidArgumentException   (astuce : #[DataProvider])
    //  - coupons WELCOME10 / FIXED5 / FREESHIP (seuils inclus/exclus), coupon inconnu, casse
    //  - livraison offerte à partir de 50 € APRÈS remise
    //  - produit inconnu -> UnknownProductException
}
