<?php

declare(strict_types=1);

namespace MiniShop;

use Brick\Math\BigDecimal;

/** Catalogue en mémoire (volontairement simple). */
final class Catalog
{
    /** @var array<string, Product>|null */
    private static ?array $products = null;

    /** @return list<Product> */
    public static function listProducts(): array
    {
        return array_values(self::products());
    }

    /** @throws UnknownProductException si le produit n'existe pas */
    public static function getProduct(string $productId): Product
    {
        return self::products()[$productId] ?? throw new UnknownProductException($productId);
    }

    /** @return array<string, Product> */
    private static function products(): array
    {
        if (null === self::$products) {
            self::$products = [];
            foreach ([
                new Product('mug', 'Mug « It works on my machine »', BigDecimal::of('12.50'), 120),
                new Product('tshirt', 'T-shirt « Green pipeline »', BigDecimal::of('19.90'), 40),
                new Product('sticker', 'Lot de stickers YAML', BigDecimal::of('2.45'), 1000),
                new Product('hoodie', 'Sweat « Shift left »', BigDecimal::of('44.00'), 15),
                new Product('book', 'Livre « Tests automatisés en 21 jours »', BigDecimal::of('29.99'), 8),
            ] as $product) {
                self::$products[$product->id] = $product;
            }
        }

        return self::$products;
    }
}
