<?php

declare(strict_types=1);

namespace MiniShop;

use Brick\Math\BigDecimal;

/** Ligne d'un devis. */
final readonly class Line
{
    public function __construct(
        public string $productId,
        public int $qty,
        public BigDecimal $unitPrice,
        public BigDecimal $total,
    ) {
    }
}
