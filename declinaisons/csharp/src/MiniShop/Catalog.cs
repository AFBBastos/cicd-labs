namespace MiniShop;

/// <summary>Produit du catalogue.</summary>
/// <param name="Id">Identifiant technique (ex. « mug »).</param>
/// <param name="Name">Libellé affiché.</param>
/// <param name="Price">Prix unitaire TTC en euros.</param>
/// <param name="Stock">Quantité en stock.</param>
public sealed record Product(string Id, string Name, decimal Price, int Stock);

/// <summary>Catalogue en mémoire (volontairement simple).</summary>
public static class Catalog
{
    private static readonly Product[] Products =
    [
        new("mug", "Mug « It works on my machine »", 12.50m, 120),
        new("tshirt", "T-shirt « Green pipeline »", 19.90m, 40),
        new("sticker", "Lot de stickers YAML", 2.45m, 1000),
        new("hoodie", "Sweat « Shift left »", 44.00m, 15),
        new("book", "Livre « Tests automatisés en 21 jours »", 29.99m, 8),
    ];

    private static readonly Dictionary<string, Product> ById = Products.ToDictionary(p => p.Id);

    /// <summary>Tous les produits, dans l'ordre du catalogue.</summary>
    public static IReadOnlyList<Product> ListProducts() => Products;

    /// <summary>Retourne un produit par son identifiant.</summary>
    /// <exception cref="KeyNotFoundException">Produit inconnu.</exception>
    public static Product GetProduct(string productId)
    {
        if (!ById.TryGetValue(productId, out var product))
        {
            throw new KeyNotFoundException($"Produit inconnu : {productId}");
        }

        return product;
    }
}
