package fr.minishop.api;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import java.util.List;

/** Panier reçu par l'API : articles et coupon facultatif. */
public record Cart(
    List<@NotNull @Valid CartItem> items, @Schema(example = "WELCOME10") String coupon) {

  /** Un panier sans champ « items » (ou avec « items » nul) est un panier vide. */
  public Cart {
    items = items == null ? List.of() : List.copyOf(items);
  }
}
