package fr.minishop;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * Règles de calcul du panier MiniShop.
 *
 * <p>Règles métier (voir specs/pricing.feature à la racine du dépôt) :
 *
 * <ul>
 *   <li>Prix exprimés en euros TTC, arrondis au centime (RoundingMode.HALF_UP).
 *   <li>Quantité : entier entre 1 et 99, sinon IllegalArgumentException.
 *   <li>Remise volume : -5 % sur une ligne dès 10 unités du même produit.
 *   <li>Coupons (un seul par panier ; coupon inconnu : IllegalArgumentException) :
 *       <ul>
 *         <li>WELCOME10 : -10 % sur le sous-total si sous-total >= 20 €
 *         <li>FIXED5 : -5 € si sous-total >= 30 €
 *         <li>FREESHIP : livraison offerte
 *       </ul>
 *   <li>Livraison : 4,90 € ; offerte si le total après remise >= 50 €.
 *   <li>Panier vide : total 0, pas de frais de livraison.
 * </ul>
 *
 * <p>Les montants sont des BigDecimal, jamais des double.
 */
public final class Pricing {

  public static final BigDecimal SHIPPING_FEE = new BigDecimal("4.90");
  public static final BigDecimal FREE_SHIPPING_THRESHOLD = new BigDecimal("50.00");
  public static final int BULK_QTY = 10;
  public static final BigDecimal BULK_RATE = new BigDecimal("0.05");
  public static final int MAX_QTY = 99;
  public static final Set<String> COUPONS = Set.of("WELCOME10", "FIXED5", "FREESHIP");

  private static final BigDecimal ZERO = new BigDecimal("0.00");

  private Pricing() {}

  /** Arrondit un montant au centime (arrondi commercial). */
  public static BigDecimal money(BigDecimal value) {
    return money(value, roundingMode(System.getenv("MINISHOP_BUG")));
  }

  /** Variante pratique : {@code money("0.125")}. */
  public static BigDecimal money(String value) {
    return money(new BigDecimal(value));
  }

  /** Arrondit un montant au centime avec le mode d'arrondi indiqué. */
  public static BigDecimal money(BigDecimal value, RoundingMode mode) {
    return value.setScale(2, mode);
  }

  /**
   * Mode d'arrondi selon la valeur de la variable d'environnement MINISHOP_BUG.
   *
   * <p>Bug injectable pour les démos de régression : "rounding" donne l'arrondi bancaire (HALF_EVEN
   * : 0.125 -> 0.12) au lieu de l'arrondi commercial (HALF_UP : 0.125 -> 0.13).
   */
  public static RoundingMode roundingMode(String bug) {
    if ("rounding".equals(bug)) {
      return RoundingMode.HALF_EVEN;
    }
    return RoundingMode.HALF_UP;
  }

  /** Total d'une ligne, remise volume incluse. */
  public static BigDecimal lineTotal(BigDecimal unitPrice, int qty) {
    if (qty < 1 || qty > MAX_QTY) {
      throw new IllegalArgumentException("Quantité hors limites (1.." + MAX_QTY + ") : " + qty);
    }
    BigDecimal gross = unitPrice.multiply(BigDecimal.valueOf(qty));
    if (qty >= BULK_QTY) {
      gross = gross.multiply(BigDecimal.ONE.subtract(BULK_RATE));
    }
    return money(gross);
  }

  /** Montant de la remise apportée par le coupon (positif). */
  public static BigDecimal couponDiscount(BigDecimal subtotal, String coupon) {
    if (coupon == null || coupon.isEmpty()) {
      return ZERO;
    }
    String code = normalize(coupon);
    if (!COUPONS.contains(code)) {
      throw new IllegalArgumentException("Coupon inconnu : " + coupon);
    }
    if (code.equals("WELCOME10") && subtotal.compareTo(new BigDecimal("20")) >= 0) {
      return money(subtotal.multiply(new BigDecimal("0.10")));
    }
    if (code.equals("FIXED5") && subtotal.compareTo(new BigDecimal("30")) >= 0) {
      return new BigDecimal("5.00");
    }
    return ZERO;
  }

  /** Frais de livraison pour un montant après remise. */
  public static BigDecimal shippingCost(
      BigDecimal amountAfterDiscount, String coupon, boolean empty) {
    if (empty) {
      return ZERO;
    }
    if (coupon != null && normalize(coupon).equals("FREESHIP")) {
      return ZERO;
    }
    if (amountAfterDiscount.compareTo(FREE_SHIPPING_THRESHOLD) >= 0) {
      return ZERO;
    }
    return SHIPPING_FEE;
  }

  /** Calcule un devis sans coupon. */
  public static Quote quote(List<Item> items) {
    return quote(items, null);
  }

  /** Calcule un devis pour une liste d'articles et un coupon facultatif (null ou "" : aucun). */
  public static Quote quote(List<Item> items, String coupon) {
    List<Line> lines = new ArrayList<>();
    BigDecimal sum = BigDecimal.ZERO;
    for (Item item : items) {
      Product product = Catalog.getProduct(item.productId()); // NoSuchElementException si inconnu
      BigDecimal total = lineTotal(product.price(), item.qty());
      lines.add(new Line(product.id(), item.qty(), product.price(), total));
      sum = sum.add(total);
    }
    boolean empty = lines.isEmpty();
    BigDecimal subtotal = money(sum);
    BigDecimal discount = empty ? ZERO : couponDiscount(subtotal, coupon);
    BigDecimal after = subtotal.subtract(discount);
    BigDecimal shipping = shippingCost(after, coupon, empty);
    BigDecimal total = money(after.add(shipping));
    String code = (coupon == null || coupon.isEmpty()) ? null : normalize(coupon);
    return new Quote(lines, subtotal, discount, shipping, total, code);
  }

  private static String normalize(String coupon) {
    return coupon.strip().toUpperCase(Locale.ROOT);
  }
}
