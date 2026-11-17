<?php

declare(strict_types=1);

namespace MiniShop\Http;

/**
 * Commandes gardées dans APCu, la mémoire partagée du serveur PHP.
 *
 * En PHP, chaque requête repart d'un état vierge : sans mémoire partagée, une commande créée
 * par une requête serait invisible de la suivante.
 */
final class ApcuOrderRepository implements OrderRepository
{
    private const string PREFIX = 'minishop_order_';

    public function save(string $id, array $order): void
    {
        apcu_store(self::PREFIX.$id, $order);
    }

    public function find(string $id): ?array
    {
        $order = apcu_fetch(self::PREFIX.$id);

        return \is_array($order) ? $order : null;
    }
}
