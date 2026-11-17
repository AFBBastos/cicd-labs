/**
 * Catalogue en mémoire (volontairement simple).
 */

import Decimal from 'decimal.js';

/**
 * @typedef {object} Product
 * @property {string} id
 * @property {string} name
 * @property {Decimal} price Prix unitaire TTC en euros.
 * @property {number} stock
 */

/** Erreur levée quand l'identifiant ne correspond à aucun produit du catalogue. */
export class UnknownProductError extends Error {
  /** @param {string} productId */
  constructor(productId) {
    super(`Produit inconnu : ${productId}`);
    this.name = 'UnknownProductError';
  }
}

/** @type {Map<string, Product>} */
const PRODUCTS = new Map(
  [
    { id: 'mug', name: 'Mug « It works on my machine »', price: new Decimal('12.50'), stock: 120 },
    { id: 'tshirt', name: 'T-shirt « Green pipeline »', price: new Decimal('19.90'), stock: 40 },
    { id: 'sticker', name: 'Lot de stickers YAML', price: new Decimal('2.45'), stock: 1000 },
    { id: 'hoodie', name: 'Sweat « Shift left »', price: new Decimal('44.00'), stock: 15 },
    {
      id: 'book',
      name: 'Livre « Tests automatisés en 21 jours »',
      price: new Decimal('29.99'),
      stock: 8,
    },
  ].map((product) => [product.id, Object.freeze(product)]),
);

/** @returns {Product[]} */
export function listProducts() {
  return [...PRODUCTS.values()];
}

/**
 * @param {string} productId
 * @returns {Product}
 * @throws {UnknownProductError} si le produit n'existe pas.
 */
export function getProduct(productId) {
  const product = PRODUCTS.get(productId);
  if (product === undefined) {
    throw new UnknownProductError(productId);
  }
  return product;
}
