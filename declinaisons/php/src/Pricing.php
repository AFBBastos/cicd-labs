<?php

declare(strict_types=1);

namespace MiniShop;

use Brick\Math\BigDecimal;
use Brick\Math\BigNumber;
use Brick\Math\RoundingMode;

/**
 * Règles de calcul du panier MiniShop.
 *
 * Règles métier (voir specs/pricing.feature à la racine du dépôt) :
 * - Prix exprimés en euros TTC, arrondis au centime (arrondi commercial, HALF_UP).
 * - Quantité : entier entre 1 et 99, sinon InvalidArgumentException.
 * - Remise volume : -5 % sur une ligne dès 10 unités du même produit.
 * - Coupons :
 *     * WELCOME10 : -10 % sur le sous-total si sous-total >= 20 €
 *     * FIXED5    : -5 € si sous-total >= 30 €
 *     * FREESHIP  : livraison offerte
 *   Un seul coupon par panier. Coupon inconnu -> InvalidArgumentException.
 * - Livraison : 4,90 € ; offerte si le total après remise >= 50 €.
 * - Panier vide : total 0, pas de frais de livraison.
 *
 * Les montants sont des BigDecimal (décimaux exacts), jamais des flottants.
 */
final class Pricing
{
    public const string SHIPPING_FEE = '4.90';
    public const string FREE_SHIPPING_THRESHOLD = '50.00';
    public const int BULK_QTY = 10;
    public const string BULK_RATE = '0.05';
    public const int MAX_QTY = 99;
    public const array COUPONS = ['WELCOME10', 'FIXED5', 'FREESHIP'];

    /** Arrondit un montant au centime (arrondi commercial). */
    public static function money(BigNumber|float|int|string $value): BigDecimal
    {
        $decimal = BigDecimal::of(\is_float($value) ? (string) $value : $value);
        // Bug injectable pour les démos de régression (MINISHOP_BUG=rounding)
        if ('rounding' === getenv('MINISHOP_BUG')) {
            return $decimal->toScale(2, RoundingMode::HalfEven); // arrondi bancaire : 0.125 -> 0.12
        }

        return $decimal->toScale(2, RoundingMode::HalfUp);
    }

    /**
     * Total d'une ligne, remise volume incluse.
     *
     * $qty est volontairement non typé : la règle « la quantité doit être un entier »
     * se vérifie ici et se teste (chaîne, flottant, booléen, null).
     */
    public static function lineTotal(BigDecimal $unitPrice, mixed $qty): BigDecimal
    {
        if (!\is_int($qty)) {
            throw new \InvalidArgumentException('La quantité doit être un entier');
        }
        if ($qty < 1 || $qty > self::MAX_QTY) {
            throw new \InvalidArgumentException(sprintf('Quantité hors limites (1..%d) : %d', self::MAX_QTY, $qty));
        }
        $gross = $unitPrice->multipliedBy($qty);
        if ($qty >= self::BULK_QTY) {
            $gross = $gross->multipliedBy(BigDecimal::one()->minus(self::BULK_RATE));
        }

        return self::money($gross);
    }

    /** Montant de la remise apportée par le coupon (positif). */
    public static function couponDiscount(BigDecimal $subtotal, ?string $coupon): BigDecimal
    {
        if (null === $coupon || '' === $coupon) {
            return BigDecimal::of('0.00');
        }
        $code = strtoupper(trim($coupon));
        if (!\in_array($code, self::COUPONS, true)) {
            throw new \InvalidArgumentException("Coupon inconnu : {$coupon}");
        }
        if ('WELCOME10' === $code && $subtotal->isGreaterThanOrEqualTo('20')) {
            return self::money($subtotal->multipliedBy('0.10'));
        }
        if ('FIXED5' === $code && $subtotal->isGreaterThanOrEqualTo('30')) {
            return BigDecimal::of('5.00');
        }

        return BigDecimal::of('0.00');
    }

    /** Frais de livraison pour un montant APRÈS remise. */
    public static function shippingCost(BigDecimal $amountAfterDiscount, ?string $coupon, bool $empty): BigDecimal
    {
        if ($empty) {
            return BigDecimal::of('0.00');
        }
        if (null !== $coupon && 'FREESHIP' === strtoupper(trim($coupon))) {
            return BigDecimal::of('0.00');
        }
        if ($amountAfterDiscount->isGreaterThanOrEqualTo(self::FREE_SHIPPING_THRESHOLD)) {
            return BigDecimal::of('0.00');
        }

        return BigDecimal::of(self::SHIPPING_FEE);
    }

    /**
     * Calcule un devis pour une liste d'items ['product_id' => ..., 'qty' => ...].
     *
     * @param list<array{product_id: string, qty: mixed}> $items
     *
     * @throws UnknownProductException   si un produit n'existe pas
     * @throws \InvalidArgumentException si une quantité ou le coupon est invalide
     */
    public static function quote(array $items, ?string $coupon = null): Quote
    {
        $quote = new Quote(null !== $coupon && '' !== $coupon ? strtoupper(trim($coupon)) : null);
        $sum = BigDecimal::zero();
        foreach ($items as $item) {
            $product = Catalog::getProduct($item['product_id']);
            $total = self::lineTotal($product->price, $item['qty']);
            $quote->lines[] = new Line($product->id, $item['qty'], $product->price, $total);
            $sum = $sum->plus($total);
        }
        $empty = [] === $quote->lines;
        $quote->subtotal = self::money($sum);
        $quote->discount = $empty ? BigDecimal::of('0.00') : self::couponDiscount($quote->subtotal, $coupon);
        $after = $quote->subtotal->minus($quote->discount);
        $quote->shipping = self::shippingCost($after, $coupon, $empty);
        $quote->total = self::money($after->plus($quote->shipping));

        return $quote;
    }
}
