package fr.minishop;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * Tests unitaires des règles de prix — POINT DE DÉPART (Atelier 1).
 *
 * <p>Complétez ce fichier : objectif >= 90 % de couverture de branches sur Pricing.java.
 */
@Tag("unit")
class PricingTest {

  @Test
  @DisplayName("0.125 s'arrondit à 0.13 (HALF_UP), pas 0.12")
  void moneyArrondiCommercial() {
    assertThat(Pricing.money("0.125")).isEqualByComparingTo("0.13");
  }

  @Test
  void lineTotalSansRemise() {
    assertThat(Pricing.lineTotal(new BigDecimal("12.50"), 2)).isEqualByComparingTo("25.00");
  }

  @Test
  @DisplayName("Un panier vide coûte 0 € : pas de frais de livraison")
  void quotePanierVide() {
    Quote q = Pricing.quote(List.of());
    assertThat(q.total()).isEqualByComparingTo("0.00");
    assertThat(q.shipping()).isEqualByComparingTo("0.00");
  }

  // TODO Atelier 1 :
  //  - remise volume à partir de 10 unités (et pas à 9 !)
  //  - quantités invalides (0, 100, -1) -> IllegalArgumentException
  //    (astuce : @ParameterizedTest + @ValueSource ; "2" et true ne compilent pas : voir l'énoncé)
  //  - coupons WELCOME10 / FIXED5 / FREESHIP (seuils inclus/exclus), coupon inconnu, casse
  //  - livraison offerte à partir de 50 € APRÈS remise
  //  - produit inconnu -> NoSuchElementException
}
