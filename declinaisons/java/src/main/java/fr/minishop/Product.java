package fr.minishop;

import java.math.BigDecimal;

/** Produit du catalogue. */
public record Product(String id, String name, BigDecimal price, int stock) {}
