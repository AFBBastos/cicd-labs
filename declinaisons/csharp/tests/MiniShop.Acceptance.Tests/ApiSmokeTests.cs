// Tests d'API — POINT DE DÉPART (Atelier 9).
//
// Prérequis : application lancée (docker compose up -d --build à la racine du dépôt).
// Lancer :    dotnet test --filter "Category=api"

using System.Net;
using System.Net.Http.Json;
using System.Text.Json;

namespace MiniShop.Acceptance.Tests;

[Trait("Category", "api")]
public class ApiSmokeTests
{
    private static readonly HttpClient Client = new() { BaseAddress = new Uri(AppUrl.Value) };

    [Fact]
    public async Task Health()
    {
        using var response = await Client.GetAsync("/health");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var json = await response.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal("ok", json.GetProperty("status").GetString());
    }

    [Fact]
    public async Task Liste_produits()
    {
        using var response = await Client.GetAsync("/products");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var json = await response.Content.ReadFromJsonAsync<JsonElement>();
        var ids = json.EnumerateArray().Select(p => p.GetProperty("id").GetString()).ToHashSet();
        Assert.Contains("mug", ids);
        Assert.Contains("tshirt", ids);
    }

    // TODO Atelier 9 : /products/{id} (200, 404), /cart/quote (200, 404, 422), /orders (201, 422), GET /orders/{id}
}
