// Tests unitaires des règles de prix — POINT DE DÉPART (Atelier 1).
//
// Complétez ce fichier : objectif >= 90 % de couverture de branches sur src/MiniShop/Pricing.cs.

namespace MiniShop.Tests;

[Trait("Category", "unit")]
public class PricingTests
{
    /// <summary>0.125 s'arrondit à 0.13 (arrondi commercial), pas 0.12.</summary>
    [Fact]
    public void Money_arrondi_commercial()
    {
        Assert.Equal(0.13m, Pricing.Money(0.125m));
    }

    [Fact]
    public void LineTotal_sans_remise()
    {
        Assert.Equal(25.00m, Pricing.LineTotal(12.50m, 2));
    }

    /// <summary>Un panier vide coûte 0 € : pas de frais de livraison.</summary>
    [Fact]
    public void Quote_panier_vide()
    {
        var q = Pricing.Quote([]);

        Assert.Equal(0.00m, q.Total);
        Assert.Equal(0.00m, q.Shipping);
    }

    // TODO Atelier 1 :
    //  - remise volume à partir de 10 unités (et pas à 9 !)
    //  - quantités invalides (0, 100, -1) -> ArgumentOutOfRangeException   (astuce : [Theory] + [InlineData])
    //  - coupons WELCOME10 / FIXED5 / FREESHIP (seuils inclus/exclus), coupon inconnu, casse
    //  - livraison offerte à partir de 50 € APRÈS remise
    //  - produit inconnu -> KeyNotFoundException
}
