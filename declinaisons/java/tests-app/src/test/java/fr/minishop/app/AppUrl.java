package fr.minishop.app;

/**
 * Adresse de l'application testée.
 *
 * <p>Ordre de lecture : propriété {@code -Dapp.url=…}, puis variable d'environnement {@code
 * APP_URL}, puis {@code http://localhost:8000}.
 */
public final class AppUrl {

  public static final String DEFAUT = "http://localhost:8000";

  private AppUrl() {}

  public static String get() {
    String url = System.getProperty("app.url");
    if (url == null || url.isBlank()) {
      url = System.getenv("APP_URL");
    }
    if (url == null || url.isBlank()) {
      url = DEFAUT;
    }
    return url;
  }
}
