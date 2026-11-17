package fr.minishop.api;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;

/** Article d'un panier reçu par l'API. */
public record CartItem(
    @JsonProperty("product_id") @NotNull @Schema(example = "mug") String productId,
    @NotNull @Min(1) @Max(99) @Schema(example = "2") Integer qty) {

  /**
   * Lecture depuis le JSON, avec les mêmes tolérances que l'application Python : la quantité peut
   * être un entier, un décimal sans partie fractionnaire (2.0) ou une chaîne d'entier ("2").
   */
  @JsonCreator
  static CartItem of(
      @JsonProperty("product_id") Object productId, @JsonProperty("qty") Object qty) {
    if (productId != null && !(productId instanceof String)) {
      throw new IllegalArgumentException("product_id doit être une chaîne");
    }
    return new CartItem((String) productId, toInteger(qty));
  }

  private static Integer toInteger(Object value) {
    if (value == null) {
      return null;
    }
    if (value instanceof Number || value instanceof String) {
      try {
        return new BigDecimal(value.toString().strip()).intValueExact();
      } catch (ArithmeticException | NumberFormatException exc) {
        throw new IllegalArgumentException("qty doit être un entier", exc);
      }
    }
    throw new IllegalArgumentException("qty doit être un entier");
  }
}
