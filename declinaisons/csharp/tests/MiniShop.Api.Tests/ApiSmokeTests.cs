// Tests d'API en mémoire — POINT DE DÉPART (Atelier 9).
//
// WebApplicationFactory démarre l'application dans le processus de test : rapide, pas de serveur à lancer.
// Lancer : dotnet test --filter "Category=api"

using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;

namespace MiniShop.Api.Tests;

[Trait("Category", "api")]
public class ApiSmokeTests(WebApplicationFactory<Program> factory) : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _client = factory.CreateClient();

    [Fact]
    public async Task Health()
    {
        using var response = await _client.GetAsync("/health");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var json = await response.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal("ok", json.GetProperty("status").GetString());
    }

    [Fact]
    public async Task Liste_produits()
    {
        using var response = await _client.GetAsync("/products");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var json = await response.Content.ReadFromJsonAsync<JsonElement>();
        var ids = json.EnumerateArray().Select(p => p.GetProperty("id").GetString()).ToHashSet();
        Assert.Contains("mug", ids);
        Assert.Contains("tshirt", ids);
    }

    // TODO Atelier 9 : /products/{id} (200, 404), /cart/quote (200, 404, 422), /orders (201, 422), GET /orders/{id}
}
