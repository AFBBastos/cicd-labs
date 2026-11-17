<?php

declare(strict_types=1);

// Règles de style : PSR-12 + jeu Symfony, sur les sources, les tests (boîte noire comprise) et les outils.
$finder = (new PhpCsFixer\Finder())
    ->in([__DIR__.'/src', __DIR__.'/tests', __DIR__.'/tools', __DIR__.'/boite-noire/tests'])
    ->append([__FILE__]);

return (new PhpCsFixer\Config())
    ->setRiskyAllowed(true)
    ->setRules([
        '@PSR12' => true,
        '@Symfony' => true,
        'declare_strict_types' => true,
        'php_unit_method_casing' => ['case' => 'camel_case'],
    ])
    ->setFinder($finder);
