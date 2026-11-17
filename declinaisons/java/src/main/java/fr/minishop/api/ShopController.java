package fr.minishop.api;

import fr.minishop.Catalog;
import fr.minishop.Item;
import fr.minishop.Pricing;
import fr.minishop.Product;
import fr.minishop.Quote;
import io.micrometer.core.instrument.Counter;
import io.micrometer.prometheusmetrics.PrometheusMeterRegistry;
import io.swagger.v3.oas.annotations.Hidden;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import jakarta.validation.Valid;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/** Routes de l'API MiniShop. Les noms des paramètres de chemin font partie du contrat. */
@RestController
public class ShopController {

  private final Map<String, Map<String, Object>> orders = new ConcurrentHashMap<>();
  private final PrometheusMeterRegistry registry;
  private final Counter ordersCounter;
  private final String version;

  public ShopController(
      PrometheusMeterRegistry registry, @Value("${minishop.version}") String version) {
    this.registry = registry;
    this.version = version;
    this.ordersCounter =
        Counter.builder("minishop.orders").description("Commandes créées").register(registry);
  }

  @Hidden
  @GetMapping(value = "/", produces = "text/html;charset=UTF-8")
  public Resource home() {
    return new ClassPathResource("static/index.html");
  }

  @GetMapping("/health")
  public Map<String, String> health() {
    Map<String, String> body = new LinkedHashMap<>();
    body.put("status", "ok");
    body.put("version", version);
    return body;
  }

  @Hidden
  @GetMapping("/metrics")
  public ResponseEntity<String> metrics() {
    return ResponseEntity.ok()
        .contentType(MediaType.parseMediaType("text/plain; version=0.0.4; charset=utf-8"))
        .body(registry.scrape());
  }

  @GetMapping("/products")
  public List<Map<String, Object>> products() {
    return Catalog.listProducts().stream().map(ShopController::productBody).toList();
  }

  @GetMapping("/products/{product_id}")
  @ApiResponse(responseCode = "200", description = "Produit")
  @ApiResponse(responseCode = "404", description = "Produit inconnu")
  public Map<String, Object> product(@PathVariable("product_id") String productId) {
    try {
      return productBody(Catalog.getProduct(productId));
    } catch (NoSuchElementException exc) {
      throw new ApiException(HttpStatus.NOT_FOUND, exc.getMessage());
    }
  }

  @PostMapping("/cart/quote")
  @ApiResponse(responseCode = "200", description = "Devis")
  @ApiResponse(responseCode = "404", description = "Produit inconnu")
  @ApiResponse(responseCode = "422", description = "Panier invalide")
  public Map<String, Object> cartQuote(@Valid @RequestBody Cart cart) {
    return quote(cart).asMap();
  }

  @PostMapping("/orders")
  @ResponseStatus(HttpStatus.CREATED)
  @ApiResponse(responseCode = "201", description = "Commande créée")
  @ApiResponse(responseCode = "404", description = "Produit inconnu")
  @ApiResponse(responseCode = "422", description = "Panier vide ou invalide")
  public Map<String, Object> createOrder(@Valid @RequestBody Cart cart) {
    if (cart.items().isEmpty()) {
      throw new ApiException(HttpStatus.UNPROCESSABLE_ENTITY, "Panier vide");
    }
    Quote quote = quote(cart);
    String orderId = UUID.randomUUID().toString().replace("-", "").substring(0, 12);
    Map<String, Object> order = new LinkedHashMap<>();
    order.put("id", orderId);
    order.putAll(quote.asMap());
    orders.put(orderId, order);
    ordersCounter.increment();
    return order;
  }

  @GetMapping("/orders/{order_id}")
  @ApiResponse(responseCode = "200", description = "Commande")
  @ApiResponse(responseCode = "404", description = "Commande introuvable")
  public Map<String, Object> getOrder(@PathVariable("order_id") String orderId) {
    Map<String, Object> order = orders.get(orderId);
    if (order == null) {
      throw new ApiException(HttpStatus.NOT_FOUND, "Commande introuvable");
    }
    return order;
  }

  private static Quote quote(Cart cart) {
    List<Item> items = cart.items().stream().map(i -> new Item(i.productId(), i.qty())).toList();
    try {
      return Pricing.quote(items, cart.coupon());
    } catch (NoSuchElementException exc) {
      throw new ApiException(HttpStatus.NOT_FOUND, exc.getMessage());
    } catch (IllegalArgumentException exc) {
      throw new ApiException(HttpStatus.UNPROCESSABLE_ENTITY, exc.getMessage());
    }
  }

  private static Map<String, Object> productBody(Product p) {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("id", p.id());
    body.put("name", p.name());
    body.put("price", p.price().toPlainString());
    body.put("stock", p.stock());
    return body;
  }
}
