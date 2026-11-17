// Règles de calcul du panier MiniShop.
//
// Règles métier (voir specs/pricing.feature à la racine du dépôt) :
// - Prix exprimés en euros TTC, arrondis au centime (arrondi commercial : MidpointRounding.AwayFromZero).
// - Quantité : entier entre 1 et 99, sinon ArgumentOutOfRangeException.
// - Remise volume : -5 % sur une ligne dès 10 unités du même produit.
// - Coupons :
//     * WELCOME10 : -10 % sur le sous-total si sous-total >= 20 €
//     * FIXED5    : -5 € si sous-total >= 30 €
//     * FREESHIP  : livraison offerte
//   Un seul coupon par panier. Coupon inconnu -> ArgumentException.
// - Livraison : 4,90 € ; offerte si le total après remise >= 50 €.
// - Panier vide : total 0, pas de frais de livraison.
//
// Les montants sont des « decimal » (type décimal exact), jamais des « double ».

using System.Globalization;

namespace MiniShop;

/// <summary>Article demandé : identifiant du produit et quantité.</summary>
public sealed record CartItem(string ProductId, int Qty);

/// <summary>Ligne de devis.</summary>
public sealed record Line(string ProductId, int Qty, decimal UnitPrice, decimal Total);

/// <summary>Devis d'un panier.</summary>
public sealed class Quote
{
    /// <summary>Lignes du devis, dans l'ordre du panier.</summary>
    public IList<Line> Lines { get; } = [];

    /// <summary>Somme des lignes, remises volume incluses.</summary>
    public decimal Subtotal { get; set; }

    /// <summary>Remise apportée par le coupon (montant positif).</summary>
    public decimal Discount { get; set; }

    /// <summary>Frais de livraison.</summary>
    public decimal Shipping { get; set; }

    /// <summary>Montant à payer.</summary>
    public decimal Total { get; set; }

    /// <summary>Code du coupon, normalisé (majuscules, sans espaces), ou null.</summary>
    public string? Coupon { get; init; }

    /// <summary>
    /// Représentation sérialisable (équivalent de <c>as_dict()</c> en Python) : les montants sont des chaînes
    /// à deux décimales, avec un point, quelle que soit la culture du poste.
    /// </summary>
    public IDictionary<string, object?> AsDictionary()
    {
        return new Dictionary<string, object?>
        {
            ["lines"] = Lines
                .Select(ln => new Dictionary<string, object?>
                {
                    ["product_id"] = ln.ProductId,
                    ["qty"] = ln.Qty,
                    ["unit_price"] = Format(ln.UnitPrice),
                    ["total"] = Format(ln.Total),
                })
                .ToList(),
            ["subtotal"] = Format(Subtotal),
            ["discount"] = Format(Discount),
            ["shipping"] = Format(Shipping),
            ["total"] = Format(Total),
            ["coupon"] = Coupon,
        };
    }

    // Sans culture invariante, un poste en fr-FR écrirait « 27,40 » au lieu de « 27.40 ».
    private static string Format(decimal amount) => amount.ToString("F2", CultureInfo.InvariantCulture);
}

/// <summary>Fonctions de calcul du panier.</summary>
public static class Pricing
{
    /// <summary>Frais de livraison.</summary>
    public const decimal ShippingFee = 4.90m;

    /// <summary>Montant après remise à partir duquel la livraison est offerte.</summary>
    public const decimal FreeShippingThreshold = 50.00m;

    /// <summary>Quantité à partir de laquelle la remise volume s'applique.</summary>
    public const int BulkQty = 10;

    /// <summary>Taux de la remise volume.</summary>
    public const decimal BulkRate = 0.05m;

    /// <summary>Quantité maximale par ligne.</summary>
    public const int MaxQty = 99;

    private static readonly HashSet<string> Coupons = ["WELCOME10", "FIXED5", "FREESHIP"];

    /// <summary>Arrondit un montant au centime (arrondi commercial).</summary>
    public static decimal Money(decimal value)
    {
        // Bug injectable pour les démos de régression (MINISHOP_BUG=rounding)
        if (Environment.GetEnvironmentVariable("MINISHOP_BUG") == "rounding")
        {
            return Math.Round(value, 2, MidpointRounding.ToEven); // arrondi bancaire : 0.125 -> 0.12
        }

        return Math.Round(value, 2, MidpointRounding.AwayFromZero);
    }

    /// <summary>Total d'une ligne, remise volume incluse.</summary>
    /// <exception cref="ArgumentOutOfRangeException">Quantité hors de l'intervalle 1..99.</exception>
    public static decimal LineTotal(decimal unitPrice, int qty)
    {
        if (qty < 1 || qty > MaxQty)
        {
            throw new ArgumentOutOfRangeException(nameof(qty), qty, $"Quantité hors limites (1..{MaxQty}) : {qty}");
        }

        var gross = unitPrice * qty;
        if (qty >= BulkQty)
        {
            gross *= 1 - BulkRate;
        }

        return Money(gross);
    }

    /// <summary>Montant de la remise apportée par le coupon (positif).</summary>
    /// <exception cref="ArgumentException">Coupon inconnu.</exception>
    public static decimal CouponDiscount(decimal subtotal, string? coupon)
    {
        if (string.IsNullOrEmpty(coupon))
        {
            return 0.00m;
        }

        var code = Normalize(coupon);
        if (!Coupons.Contains(code))
        {
            // Message seul, sans nom de paramètre : l'API le renvoie tel quel dans « detail ».
            throw new ArgumentException($"Coupon inconnu : {coupon}");
        }

        if (code == "WELCOME10" && subtotal >= 20m)
        {
            return Money(subtotal * 0.10m);
        }

        if (code == "FIXED5" && subtotal >= 30m)
        {
            return 5.00m;
        }

        return 0.00m;
    }

    /// <summary>Frais de livraison pour un montant après remise.</summary>
    public static decimal ShippingCost(decimal amountAfterDiscount, string? coupon, bool empty)
    {
        if (empty)
        {
            return 0.00m;
        }

        if (!string.IsNullOrEmpty(coupon) && Normalize(coupon) == "FREESHIP")
        {
            return 0.00m;
        }

        if (amountAfterDiscount >= FreeShippingThreshold)
        {
            return 0.00m;
        }

        return ShippingFee;
    }

    /// <summary>Calcule un devis pour une liste d'articles.</summary>
    /// <exception cref="KeyNotFoundException">Produit inconnu.</exception>
    public static Quote Quote(IEnumerable<CartItem> items, string? coupon = null)
    {
        ArgumentNullException.ThrowIfNull(items);

        var q = new Quote { Coupon = string.IsNullOrEmpty(coupon) ? null : Normalize(coupon) };
        foreach (var item in items)
        {
            var product = Catalog.GetProduct(item.ProductId); // KeyNotFoundException si inconnu
            var total = LineTotal(product.Price, item.Qty);
            q.Lines.Add(new Line(product.Id, item.Qty, product.Price, total));
        }

        var empty = q.Lines.Count == 0;
        q.Subtotal = Money(q.Lines.Sum(ln => ln.Total));
        q.Discount = empty ? 0.00m : CouponDiscount(q.Subtotal, coupon);
        var after = q.Subtotal - q.Discount;
        q.Shipping = ShippingCost(after, coupon, empty);
        q.Total = Money(after + q.Shipping);
        return q;
    }

    private static string Normalize(string coupon) => coupon.Trim().ToUpperInvariant();
}
