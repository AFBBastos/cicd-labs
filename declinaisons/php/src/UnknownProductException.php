<?php

declare(strict_types=1);

namespace MiniShop;

/**
 * Produit absent du catalogue.
 *
 * Équivalent du KeyError de la version Python : on hérite d'OutOfBoundsException
 * (« clé invalide »), ce qui permet d'attraper l'une ou l'autre.
 */
final class UnknownProductException extends \OutOfBoundsException
{
    public function __construct(string $productId)
    {
        parent::__construct("Produit inconnu : {$productId}");
    }
}
