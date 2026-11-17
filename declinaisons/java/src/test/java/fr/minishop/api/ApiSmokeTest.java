package fr.minishop.api;

import static org.hamcrest.Matchers.hasItems;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Tests d'API en mémoire — POINT DE DÉPART (Atelier 9).
 *
 * <p>MockMvc appelle l'application sans ouvrir de port : pas de serveur à lancer.
 */
@Tag("api")
@SpringBootTest
@AutoConfigureMockMvc
class ApiSmokeTest {

  @Autowired private MockMvc client;

  @Test
  void health() throws Exception {
    client
        .perform(get("/health"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("ok"));
  }

  @Test
  void listeProduits() throws Exception {
    client
        .perform(get("/products"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$[*].id", hasItems("mug", "tshirt")));
  }

  // TODO Atelier 9 : /products/{id} (200, 404), /cart/quote (200, 404, 422), /orders (201, 422),
  // GET /orders/{id}
}
