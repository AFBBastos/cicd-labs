<?php

declare(strict_types=1);

/*
 * Seuil de couverture (« quality gate ») à partir d'un rapport Cobertura de PHPUnit.
 * PHPUnit n'a pas d'équivalent à `pytest --cov-fail-under` : ce script joue ce rôle.
 *
 *   php tools/coverage-check.php reports/cobertura.xml --min-lines=85
 *   php tools/coverage-check.php reports/cobertura.xml --file=Pricing.php --min-branches=90
 *   php tools/coverage-check.php reports/cobertura.xml --markdown      (tableau pour $GITHUB_STEP_SUMMARY)
 *
 * Code de retour : 0 si les seuils sont tenus, 1 sinon, 2 si le rapport est inutilisable.
 * Les branches ne sont mesurées qu'avec Xdebug et --path-coverage (pcov ne compte que les lignes).
 */

$report = null;
$options = ['min-lines' => null, 'min-branches' => null, 'file' => null, 'markdown' => false];
/** @var list<string> $arguments */
$arguments = $_SERVER['argv'] ?? [];
foreach (array_slice($arguments, 1) as $argument) {
    if ('--markdown' === $argument) {
        $options['markdown'] = true;
    } elseif (1 === preg_match('/^--(min-lines|min-branches|file)=(.+)$/', $argument, $match)) {
        $options[$match[1]] = $match[2];
    } elseif (!str_starts_with($argument, '--') && null === $report) {
        $report = $argument;
    } else {
        fwrite(\STDERR, "Argument inconnu : {$argument}\n");
        exit(2);
    }
}
if (null === $report || !is_file($report)) {
    fwrite(\STDERR, "Rapport Cobertura introuvable. Lancez d'abord : composer coverage\n");
    exit(2);
}
$xml = simplexml_load_file($report);
if (false === $xml) {
    fwrite(\STDERR, "Rapport Cobertura illisible : {$report}\n");
    exit(2);
}

$format = static fn (?float $value): string => null === $value ? 'n/d' : number_format($value, 2, '.', '').' %';

// pcov ne mesure pas les branches : le rapport en annonce alors zéro.
$withBranches = (int) $xml['branches-valid'] > 0;

// Par fichier : [taux de lignes, taux de branches], en pourcentage.
$files = [];
foreach ($xml->xpath('//class') ?: [] as $class) {
    $files[(string) $class['filename']] = [
        100 * (float) $class['line-rate'],
        $withBranches ? 100 * (float) $class['branch-rate'] : null,
    ];
}
ksort($files);

$scope = $options['file'] ?? 'Total';
if (null === $options['file']) {
    $lines = 100 * (float) $xml['line-rate'];
    $branches = $withBranches ? 100 * (float) $xml['branch-rate'] : null;
} elseif (isset($files[$scope])) {
    [$lines, $branches] = $files[$scope];
} else {
    fwrite(\STDERR, "Fichier absent du rapport : {$scope}\n");
    exit(2);
}

if ($options['markdown']) {
    echo "| Fichier | Lignes | Branches |\n|---|---:|---:|\n";
    foreach ($files as $name => [$fileLines, $fileBranches]) {
        echo "| `{$name}` | {$format($fileLines)} | {$format($fileBranches)} |\n";
    }
    echo "| **{$scope}** | **{$format($lines)}** | **{$format($branches)}** |\n";
} else {
    echo "{$scope} : lignes {$format($lines)}, branches {$format($branches)}\n";
}

$failed = false;
foreach (['min-lines' => ['lignes', $lines], 'min-branches' => ['branches', $branches]] as $option => [$label, $value]) {
    if (null === $options[$option]) {
        continue;
    }
    $minimum = (float) $options[$option];
    if (null === $value) {
        fwrite(\STDERR, "ÉCHEC : couverture de {$label} non mesurée (Xdebug et --path-coverage requis pour les branches)\n");
        $failed = true;
    } elseif ($value < $minimum) {
        fwrite(\STDERR, "ÉCHEC : couverture de {$label} {$format($value)} < seuil {$format($minimum)}\n");
        $failed = true;
    }
}
exit($failed ? 1 : 0);
