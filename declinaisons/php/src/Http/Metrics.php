<?php

declare(strict_types=1);

namespace MiniShop\Http;

use Prometheus\CollectorRegistry;
use Prometheus\Counter;
use Prometheus\Histogram;
use Prometheus\RenderTextFormat;
use Prometheus\Storage\Adapter;
use Prometheus\Storage\InMemory;

/** Métriques Prometheus de l'application (mêmes noms et étiquettes que la version Python). */
final class Metrics
{
    public const string CONTENT_TYPE = RenderTextFormat::MIME_TYPE;

    private CollectorRegistry $registry;
    private Counter $requests;
    private Histogram $latency;
    private Counter $orders;

    public function __construct(?Adapter $storage = null)
    {
        $this->registry = new CollectorRegistry($storage ?? new InMemory(), false);
        $this->requests = $this->registry->getOrRegisterCounter(
            'minishop',
            'http_requests_total',
            'Requêtes HTTP',
            ['method', 'path', 'status'],
        );
        $this->latency = $this->registry->getOrRegisterHistogram(
            'minishop',
            'http_request_duration_seconds',
            'Latence HTTP',
            ['path'],
        );
        $this->orders = $this->registry->getOrRegisterCounter('minishop', 'orders_total', 'Commandes créées');
    }

    public function observeRequest(string $method, string $path, int $status, float $seconds): void
    {
        $this->requests->inc([$method, $path, (string) $status]);
        $this->latency->observe($seconds, [$path]);
    }

    public function orderCreated(): void
    {
        $this->orders->inc();
    }

    /** Exposition au format texte de Prometheus. */
    public function render(): string
    {
        $this->orders->incBy(0); // le compteur apparaît (à 0) avant la première commande

        return (new RenderTextFormat())->render($this->registry->getMetricFamilySamples());
    }
}
