<?php

declare(strict_types=1);

namespace MiniShop\Http;

/** Stockage des commandes (en mémoire : rien ne survit à l'arrêt de l'application). */
interface OrderRepository
{
    /** @param array<string, mixed> $order */
    public function save(string $id, array $order): void;

    /** @return array<string, mixed>|null */
    public function find(string $id): ?array;
}
