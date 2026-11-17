// Formes JSON de l'API : corps reçus et réponses. Les noms sont convertis en snake_case
// (ProductId -> product_id) et les montants sérialisés en chaînes à deux décimales (voir JsonSetup.cs).

using System.ComponentModel.DataAnnotations;

namespace MiniShop.Api;

/// <summary>Article d'un panier reçu par l'API.</summary>
public sealed record ItemRequest
{
    /// <summary>Identifiant du produit, par exemple « mug ».</summary>
    public required string ProductId { get; init; }

    /// <summary>Quantité, de 1 à 99.</summary>
    [Range(1, Pricing.MaxQty)]
    public required int Qty { get; init; }
}

/// <summary>Panier reçu par l'API.</summary>
public sealed record CartRequest
{
    /// <summary>Articles du panier.</summary>
    public IList<ItemRequest> Items { get; init; } = [];

    /// <summary>Code promo facultatif, par exemple « WELCOME10 ».</summary>
    public string? Coupon { get; init; }
}

/// <summary>Réponse de /health.</summary>
public sealed record HealthResponse(string Status, string Version);

/// <summary>Commande enregistrée : un identifiant suivi du devis.</summary>
public sealed record OrderResponse(
    string Id,
    IList<Line> Lines,
    decimal Subtotal,
    decimal Discount,
    decimal Shipping,
    decimal Total,
    string? Coupon);

/// <summary>Erreur métier : un message lisible dans « detail ».</summary>
public sealed record ErrorResponse(string Detail);

/// <summary>Une erreur de validation du corps de la requête (même forme que FastAPI : loc, msg, type).</summary>
public sealed record ValidationIssue(IList<object> Loc, string Msg, string Type);

/// <summary>Erreur de validation : la liste des problèmes dans « detail ».</summary>
public sealed record ValidationErrorResponse(IList<ValidationIssue> Detail);

/// <summary>
/// Documentation de la réponse 422 : « detail » est soit un message (erreur métier : coupon inconnu, panier
/// vide), soit la liste des problèmes de validation du corps.
/// </summary>
public sealed record UnprocessableResponse(object Detail);
