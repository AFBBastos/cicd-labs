package fr.minishop.api;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

/**
 * API HTTP MiniShop (Spring Boot).
 *
 * <p>Lancer : mvn spring-boot:run — Docs : http://localhost:8000/docs (OpenAPI : /openapi.json)
 */
@SpringBootApplication
public class MiniShopApplication {

  public static void main(String[] args) {
    SpringApplication.run(MiniShopApplication.class, args);
  }

  @Bean
  OpenAPI description(@Value("${minishop.version}") String version) {
    return new OpenAPI()
        .info(
            new Info()
                .title("MiniShop")
                .version(version)
                .description("Application fil rouge de la formation CI/CD & IA"));
  }
}
