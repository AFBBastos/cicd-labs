package fr.minishop;

import java.math.BigDecimal;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;

/** Catalogue en mémoire (volontairement simple). */
public final class Catalog {

  private static final Map<String, Product> PRODUCTS = new LinkedHashMap<>();

  static {
    for (Product p :
        List.of(
            new Product("mug", "Mug « It works on my machine »", new BigDecimal("12.50"), 120),
            new Product("tshirt", "T-shirt « Green pipeline »", new BigDecimal("19.90"), 40),
            new Product("sticker", "Lot de stickers YAML", new BigDecimal("2.45"), 1000),
            new Product("hoodie", "Sweat « Shift left »", new BigDecimal("44.00"), 15),
            new Product(
                "book", "Livre « Tests automatisés en 21 jours »", new BigDecimal("29.99"), 8))) {
      PRODUCTS.put(p.id(), p);
    }
  }

  private Catalog() {}

  public static List<Product> listProducts() {
    return List.copyOf(PRODUCTS.values());
  }

  /** Renvoie le produit, ou lève {@link NoSuchElementException} s'il est inconnu. */
  public static Product getProduct(String productId) {
    Product product = PRODUCTS.get(productId);
    if (product == null) {
      throw new NoSuchElementException("Produit inconnu : " + productId);
    }
    return product;
  }
}
