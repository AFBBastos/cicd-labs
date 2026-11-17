using System.Diagnostics;
using System.Globalization;
using System.Text.Json;
using Prometheus;

namespace MiniShop.Api;

/// <summary>Métriques Prometheus de l'application (noms et étiquettes identiques à la version Python).</summary>
public static class AppMetrics
{
    public static readonly Counter Requests = Metrics.CreateCounter(
        "minishop_http_requests_total", "Requêtes HTTP", "method", "path", "status");

    public static readonly Histogram Latency = Metrics.CreateHistogram(
        "minishop_http_request_duration_seconds", "Latence HTTP", "path");

    public static readonly Counter Orders = Metrics.CreateCounter("minishop_orders_total", "Commandes créées");

    /// <summary>Étiquette « path » des requêtes qui ne correspondent à aucune route.</summary>
    public const string UnknownRoute = "(route inconnue)";
}

/// <summary>Journal des requêtes : une ligne JSON par requête dans le fichier désigné par MINISHOP_LOG_FILE.</summary>
public sealed class RequestLog
{
    private readonly string? _path;
    private readonly Lock _lock = new();

    public RequestLog(string? path)
    {
        _path = string.IsNullOrEmpty(path) ? null : path;
        var directory = _path is null ? null : Path.GetDirectoryName(Path.GetFullPath(_path));
        if (!string.IsNullOrEmpty(directory))
        {
            Directory.CreateDirectory(directory);
        }
    }

    public void Write(string method, string path, int status, double latencyMs)
    {
        if (_path is null)
        {
            return;
        }

        var line = JsonSerializer.Serialize(new Dictionary<string, object>
        {
            ["ts"] = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0,
            ["method"] = method,
            ["path"] = path,
            ["status"] = status,
            ["latency_ms"] = Math.Round(latencyMs, 2),
        });
        lock (_lock)
        {
            File.AppendAllText(_path, line + "\n");
        }
    }
}

/// <summary>Mesure chaque requête : compteur, histogramme de latence, ligne de journal, bug « slow » injectable.</summary>
public sealed class ObserveMiddleware(RequestDelegate next, RequestLog log)
{
    public async Task InvokeAsync(HttpContext context)
    {
        ArgumentNullException.ThrowIfNull(context);
        var start = Stopwatch.GetTimestamp();

        // Bug injectable pour les ateliers de performance et de détection d'anomalies (MINISHOP_BUG=slow)
        if (Environment.GetEnvironmentVariable("MINISHOP_BUG") == "slow"
            && context.Request.Path.StartsWithSegments("/cart", StringComparison.Ordinal))
        {
#pragma warning disable CA5394 // aléa non cryptographique : il ne sert qu'à simuler une lenteur
            await Task.Delay(Random.Shared.Next(300, 801));
#pragma warning restore CA5394
        }

        try
        {
            await next(context);
        }
        finally
        {
            var elapsed = Stopwatch.GetElapsedTime(start);
            var status = context.Response.StatusCode;
            var route = (context.GetEndpoint() as RouteEndpoint)?.RoutePattern.RawText;
            var path = route ?? context.Request.Path.Value ?? "/"; // chemin réel dans le journal (repérage des scans)

            // Étiquette de métrique : le gabarit de la route (/products/{product_id}), pas l'URL réelle ; à défaut
            // le chemin d'une ressource servie (fichier statique, /docs) ; sinon une valeur fixe (404,
            // redirection...), pour qu'un scanner ne crée pas une nouvelle série Prometheus par URL demandée.
            var served = status is StatusCodes.Status200OK or StatusCodes.Status304NotModified;
            var label = route is not null || served ? path : AppMetrics.UnknownRoute;
            AppMetrics.Requests
                .WithLabels(context.Request.Method, label, status.ToString(CultureInfo.InvariantCulture))
                .Inc();
            AppMetrics.Latency.WithLabels(label).Observe(elapsed.TotalSeconds);
            log.Write(context.Request.Method, path, status, elapsed.TotalMilliseconds);
        }
    }
}
