<?php

declare(strict_types=1);

namespace MiniShop\Http;

/** Commandes gardées dans un tableau PHP : pour les tests et pour un processus unique. */
final class InMemoryOrderRepository implements OrderRepository
{
    /** @var array<string, array<string, mixed>> */
    private array $orders = [];

    public function save(string $id, array $order): void
    {
        $this->orders[$id] = $order;
    }

    public function find(string $id): ?array
    {
        return $this->orders[$id] ?? null;
    }
}
