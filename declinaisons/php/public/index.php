<?php

declare(strict_types=1);

// Point d'entrée HTTP : toutes les requêtes arrivent ici et sont confiées à l'application Slim.

use MiniShop\Http\Application;

require __DIR__.'/../vendor/autoload.php';

Application::create()->run();
