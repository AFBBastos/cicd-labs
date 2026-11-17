package fr.minishop.api;

import io.micrometer.prometheusmetrics.PrometheusConfig;
import io.micrometer.prometheusmetrics.PrometheusMeterRegistry;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Registre Prometheus déclaré à la main : les noms des métriques font partie du contrat
 * (minishop_http_requests_total, minishop_http_request_duration_seconds, minishop_orders_total).
 */
@Configuration
public class MetricsConfig {

  @Bean
  PrometheusMeterRegistry prometheusRegistry() {
    return new PrometheusMeterRegistry(PrometheusConfig.DEFAULT);
  }
}
