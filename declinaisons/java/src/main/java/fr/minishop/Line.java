package fr.minishop;

import java.math.BigDecimal;

/** Ligne d'un devis. */
public record Line(String productId, int qty, BigDecimal unitPrice, BigDecimal total) {}
