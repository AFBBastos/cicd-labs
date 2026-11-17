package fr.minishop.app.e2e;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

import com.microsoft.playwright.Page;
import com.microsoft.playwright.junit.UsePlaywright;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * Test E2E Playwright — POINT DE DÉPART (Atelier 8).
 *
 * <p>Prérequis : application lancée (docker compose up -d dans declinaisons/java). Lancer :
 * mvn test -Dgroups=e2e -Dheaded=true (pour voir le navigateur)
 */
@Tag("e2e")
@UsePlaywright(ShopOptions.class)
class ParcoursAchatTest {

  @Test
  void pageAccueil(Page page) {
    page.navigate("/");
    assertThat(page).hasTitle(Pattern.compile("MiniShop"));
    assertThat(page.getByTestId("products").locator("li")).hasCount(5);
  }

  // TODO Atelier 8 : ajouter 2 mugs, appliquer WELCOME10, vérifier le total, commander.
}
