package fr.minishop.api;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Timer;
import io.micrometer.prometheusmetrics.PrometheusMeterRegistry;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Duration;
import java.util.Locale;
import java.util.concurrent.ThreadLocalRandom;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.servlet.HandlerMapping;

/**
 * Observe chaque requête : métriques Prometheus, journal JSON (MINISHOP_LOG_FILE) et bug injectable
 * de lenteur (MINISHOP_BUG=slow : 300 à 800 ms sur les routes /cart*).
 */
@Component
public class ObservabilityFilter extends OncePerRequestFilter {

  /** Mêmes bornes que l'histogramme par défaut du client Prometheus Python. */
  private static final Duration[] BUCKETS =
      java.util.stream.Stream.of(
              5, 10, 25, 50, 75, 100, 250, 500, 750, 1000, 2500, 5000, 7500, 10000)
          .map(Duration::ofMillis)
          .toArray(Duration[]::new);

  static final String UNKNOWN_ROUTE = "(route inconnue)";

  private final PrometheusMeterRegistry registry;
  private final String bug;
  private final Path logFile;

  public ObservabilityFilter(
      PrometheusMeterRegistry registry,
      @Value("${MINISHOP_BUG:}") String bug,
      @Value("${MINISHOP_LOG_FILE:}") String logFile) {
    this.registry = registry;
    this.bug = bug;
    this.logFile = logFile.isBlank() ? null : Path.of(logFile).toAbsolutePath();
  }

  @Override
  protected void doFilterInternal(
      HttpServletRequest request, HttpServletResponse response, FilterChain chain)
      throws ServletException, IOException {
    long start = System.nanoTime();
    if ("slow".equals(bug) && request.getRequestURI().startsWith("/cart")) {
      // Seul le fil d'exécution de cette requête attend : Tomcat en a un par requête en cours,
      // les autres routes ne sont pas ralenties.
      pause(ThreadLocalRandom.current().nextLong(300, 801));
    }
    try {
      chain.doFilter(request, response);
    } finally {
      long elapsed = System.nanoTime() - start;
      String route = routeTemplate(request);
      String path = route != null ? route : request.getRequestURI(); // chemin réel dans le journal
      String method = request.getMethod();
      int status = response.getStatus();
      String label = metricLabel(route, path, status);
      Counter.builder("minishop.http.requests")
          .description("Requêtes HTTP")
          .tags("method", method, "path", label, "status", String.valueOf(status))
          .register(registry)
          .increment();
      Timer.builder("minishop.http.request.duration")
          .description("Latence HTTP")
          .tags("path", label)
          .serviceLevelObjectives(BUCKETS)
          .register(registry)
          .record(Duration.ofNanos(elapsed));
      log(method, path, status, elapsed);
    }
  }

  /**
   * Gabarit de la route (/products/{product_id}), ou null si aucune route de l'API ne correspond.
   */
  private static String routeTemplate(HttpServletRequest request) {
    Object pattern = request.getAttribute(HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE);
    if (pattern == null || pattern.toString().contains("*")) {
      return null;
    }
    return pattern.toString();
  }

  /**
   * Étiquette « path » des métriques : le gabarit de route ; à défaut le chemin d'une ressource
   * réellement servie (fichier statique, documentation) ; sinon une valeur fixe (404,
   * redirection…), pour qu'un scanner ne crée pas une nouvelle série Prometheus par URL demandée.
   */
  static String metricLabel(String route, String path, int status) {
    if (route != null) {
      return route;
    }
    return status == 200 || status == 304 ? path : UNKNOWN_ROUTE;
  }

  private synchronized void log(String method, String path, int status, long elapsedNanos)
      throws IOException {
    if (logFile == null) {
      return;
    }
    Path parent = logFile.getParent();
    if (parent != null) {
      Files.createDirectories(parent);
    }
    String line =
        String.format(
            Locale.ROOT,
            "{\"ts\": %.6f, \"method\": \"%s\", \"path\": \"%s\", \"status\": %d, \"latency_ms\": %.2f}%n",
            System.currentTimeMillis() / 1000.0,
            json(method),
            json(path),
            status,
            elapsedNanos / 1_000_000.0);
    Files.writeString(
        logFile,
        line,
        StandardCharsets.UTF_8,
        StandardOpenOption.CREATE,
        StandardOpenOption.APPEND);
  }

  /** Échappe une valeur pour une chaîne JSON (une URL inconnue peut contenir n'importe quoi). */
  private static String json(String value) {
    StringBuilder out = new StringBuilder();
    for (char c : value.toCharArray()) {
      if (c == '"' || c == '\\') {
        out.append('\\').append(c);
      } else if (c < 0x20) {
        out.append(String.format("\\u%04x", (int) c));
      } else {
        out.append(c);
      }
    }
    return out.toString();
  }

  private static void pause(long millis) {
    try {
      Thread.sleep(millis);
    } catch (InterruptedException exc) {
      Thread.currentThread().interrupt();
    }
  }
}
