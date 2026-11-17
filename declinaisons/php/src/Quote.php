<?php

declare(strict_types=1);

namespace MiniShop;

use Brick\Math\BigDecimal;

/** Devis calculé pour un panier. */
final class Quote implements \JsonSerializable
{
    /** @var list<Line> */
    public array $lines = [];
    public BigDecimal $subtotal;
    public BigDecimal $discount;
    public BigDecimal $shipping;
    public BigDecimal $total;

    public function __construct(public ?string $coupon = null)
    {
        $zero = BigDecimal::of('0.00');
        $this->subtotal = $zero;
        $this->discount = $zero;
        $this->shipping = $zero;
        $this->total = $zero;
    }

    /**
     * Équivalent de as_dict() en Python : montants sous forme de chaînes, clés en snake_case.
     *
     * @return array{
     *     lines: list<array{product_id: string, qty: int, unit_price: string, total: string}>,
     *     subtotal: string, discount: string, shipping: string, total: string, coupon: string|null
     * }
     */
    public function toArray(): array
    {
        return [
            'lines' => array_map(
                static fn (Line $line): array => [
                    'product_id' => $line->productId,
                    'qty' => $line->qty,
                    'unit_price' => (string) $line->unitPrice,
                    'total' => (string) $line->total,
                ],
                $this->lines,
            ),
            'subtotal' => (string) $this->subtotal,
            'discount' => (string) $this->discount,
            'shipping' => (string) $this->shipping,
            'total' => (string) $this->total,
            'coupon' => $this->coupon,
        ];
    }

    /** @return array<string, mixed> */
    public function jsonSerialize(): array
    {
        return $this->toArray();
    }
}
