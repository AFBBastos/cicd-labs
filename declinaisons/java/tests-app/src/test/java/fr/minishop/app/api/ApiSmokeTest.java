package fr.minishop.app.api;

import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.hasItems;

import fr.minishop.app.AppUrl;
import io.restassured.RestAssured;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * Tests d'API — POINT DE DÉPART (Atelier 9).
 *
 * <p>Prérequis : application lancée (docker compose up -d dans declinaisons/java). Lancer :
 * mvn test -Dgroups=api
 */
@Tag("api")
class ApiSmokeTest {

  @BeforeAll
  static void urlDeBase() {
    RestAssured.baseURI = AppUrl.get();
  }

  @Test
  void health() {
    given().when().get("/health").then().statusCode(200).body("status", equalTo("ok"));
  }

  @Test
  void listeProduits() {
    given().when().get("/products").then().statusCode(200).body("id", hasItems("mug", "tshirt"));
  }

  // TODO Atelier 9 : /products/{id} (200, 404), /cart/quote (200, 404, 422), /orders (201, 422),
  // GET /orders/{id}
}
