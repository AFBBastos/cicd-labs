package fr.minishop.app.e2e;

import com.microsoft.playwright.BrowserType;
import com.microsoft.playwright.junit.Options;
import com.microsoft.playwright.junit.OptionsFactory;
import fr.minishop.app.AppUrl;
import java.nio.file.Path;

/**
 * Réglages Playwright communs aux tests E2E (l'équivalent des options de pytest-playwright).
 *
 * <ul>
 *   <li>{@code -Dbrowser=firefox} : navigateur (chromium par défaut, firefox, webkit)
 *   <li>{@code -Dheaded=true} : voir le navigateur ; {@code -Dslowmo=300} : ralentir chaque action
 *   <li>traces conservées dans {@code target/test-results/} pour les tests en échec
 * </ul>
 */
public class ShopOptions implements OptionsFactory {

  @Override
  public Options getOptions() {
    return new Options()
        .setBaseUrl(AppUrl.get())
        .setBrowserName(System.getProperty("browser", "chromium"))
        .setHeadless(!Boolean.getBoolean("headed"))
        .setLaunchOptions(
            new BrowserType.LaunchOptions().setSlowMo(Integer.getInteger("slowmo", 0)))
        .setTrace(Options.Trace.RETAIN_ON_FAILURE)
        .setOutputDir(Path.of("target", "test-results"));
  }
}
