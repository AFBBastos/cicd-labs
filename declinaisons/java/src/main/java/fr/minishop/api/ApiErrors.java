package fr.minishop.api;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.NoHandlerFoundException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

/** Traduit les erreurs en réponses JSON portant un champ « detail », comme l'application Python. */
@RestControllerAdvice
public class ApiErrors {

  @ExceptionHandler(ApiException.class)
  ResponseEntity<Map<String, Object>> metier(ApiException exc) {
    return reponse(exc.status(), exc.getMessage());
  }

  /** Corps valide en JSON mais hors contrat (quantité hors limites, champ manquant…). */
  @ExceptionHandler(MethodArgumentNotValidException.class)
  ResponseEntity<Map<String, Object>> validation(MethodArgumentNotValidException exc) {
    List<Map<String, Object>> details = new ArrayList<>();
    for (FieldError error : exc.getBindingResult().getFieldErrors()) {
      details.add(
          Map.of(
              "loc", List.of("body", error.getField()),
              "msg", String.valueOf(error.getDefaultMessage()),
              "type", "value_error"));
    }
    return reponse(HttpStatus.UNPROCESSABLE_ENTITY, details);
  }

  /** Corps absent, JSON mal formé ou d'un autre type que celui attendu. */
  @ExceptionHandler({
    HttpMessageNotReadableException.class,
    HttpMediaTypeNotSupportedException.class
  })
  ResponseEntity<Map<String, Object>> corpsIllisible(Exception exc) {
    return reponse(
        HttpStatus.UNPROCESSABLE_ENTITY,
        List.of(
            Map.of("loc", List.of("body"), "msg", "Corps JSON invalide", "type", "json_invalid")));
  }

  @ExceptionHandler({NoResourceFoundException.class, NoHandlerFoundException.class})
  ResponseEntity<Map<String, Object>> routeInconnue(Exception exc) {
    return reponse(HttpStatus.NOT_FOUND, "Not Found");
  }

  @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
  ResponseEntity<Map<String, Object>> methodeRefusee(HttpRequestMethodNotSupportedException exc) {
    ResponseEntity.BodyBuilder reponse = ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED);
    Set<HttpMethod> permises = exc.getSupportedHttpMethods();
    if (permises != null) {
      reponse.allow(permises.toArray(HttpMethod[]::new)); // en-tête Allow exigé par la RFC 9110
    }
    return reponse.body(Map.of("detail", "Method Not Allowed"));
  }

  private static ResponseEntity<Map<String, Object>> reponse(HttpStatus status, Object detail) {
    return ResponseEntity.status(status).body(Map.of("detail", detail));
  }
}
