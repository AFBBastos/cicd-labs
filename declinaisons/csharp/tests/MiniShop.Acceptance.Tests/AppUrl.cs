namespace MiniShop.Acceptance.Tests;

/// <summary>Adresse de l'application testée : variable d'environnement BASE_URL, http://localhost:8000 par défaut.</summary>
public static class AppUrl
{
    public static string Value { get; } =
        (Environment.GetEnvironmentVariable("BASE_URL") ?? "http://localhost:8000").TrimEnd('/');
}
