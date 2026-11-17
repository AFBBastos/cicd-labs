package fr.minishop;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Devis : lignes, sous-total, remise, livraison, total et coupon (normalisé, ou null). */
public record Quote(
    List<Line> lines,
    BigDecimal subtotal,
    BigDecimal discount,
    BigDecimal shipping,
    BigDecimal total,
    String coupon) {

  /** Copie défensive : un devis ne change plus une fois calculé. */
  public Quote {
    lines = List.copyOf(lines);
  }

  /** Représentation sérialisable (JSON) : les montants sont des chaînes, comme dans l'API. */
  public Map<String, Object> asMap() {
    List<Map<String, Object>> lignes = new ArrayList<>();
    for (Line ln : lines) {
      Map<String, Object> ligne = new LinkedHashMap<>();
      ligne.put("product_id", ln.productId());
      ligne.put("qty", ln.qty());
      ligne.put("unit_price", ln.unitPrice().toPlainString());
      ligne.put("total", ln.total().toPlainString());
      lignes.add(ligne);
    }
    Map<String, Object> map = new LinkedHashMap<>();
    map.put("lines", lignes);
    map.put("subtotal", subtotal.toPlainString());
    map.put("discount", discount.toPlainString());
    map.put("shipping", shipping.toPlainString());
    map.put("total", total.toPlainString());
    map.put("coupon", coupon);
    return map;
  }
}
