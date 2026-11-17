package fr.minishop.api;

import org.springframework.http.HttpStatus;

/** Erreur renvoyée au client sous la forme {"detail": "..."}. */
public class ApiException extends RuntimeException {

  private static final long serialVersionUID = 1L;

  private final HttpStatus status;

  public ApiException(HttpStatus status, String detail) {
    super(detail);
    this.status = status;
  }

  public HttpStatus status() {
    return status;
  }
}
