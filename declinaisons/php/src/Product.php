<?php

declare(strict_types=1);

namespace MiniShop;

use Brick\Math\BigDecimal;

/** Produit du catalogue (immuable). */
final readonly class Product
{
    public function __construct(
        public string $id,
        public string $name,
        public BigDecimal $price,
        public int $stock,
    ) {
    }
}
