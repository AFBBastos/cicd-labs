/**
 * Règles de calcul du panier MiniShop.
 *
 * Règles métier (voir specs/pricing.feature à la racine du dépôt) :
 * - Prix exprimés en euros TTC, arrondis au centime (arrondi commercial, ROUND_HALF_UP).
 * - Quantité : entier entre 1 et 99, sinon TypeError (pas un entier) ou RangeError (hors limites).
 * - Remise volume : -5 % sur une ligne dès 10 unités du même produit.
 * - Coupons :
 *     * WELCOME10 : -10 % sur le sous-total si sous-total >= 20 €
 *     * FIXED5    : -5 € si sous-total >= 30 €
 *     * FREESHIP  : livraison offerte
 *   Un seul coupon par panier. Coupon inconnu -> RangeError.
 * - Livraison : 4,90 € ; offerte si le total après remise >= 50 €.
 * - Panier vide : total 0, pas de frais de livraison.
 *
 * Les montants sont des Decimal (decimal.js), jamais des nombres JavaScript :
 * 0.1 + 0.2 vaut 0.30000000000000004 en virgule flottante.
 */

import Decimal from 'decimal.js';

import { getProduct } from './catalog.js';

export const SHIPPING_FEE = new Decimal('4.90');
export const FREE_SHIPPING_THRESHOLD = new Decimal('50.00');
export const BULK_QTY = 10;
export const BULK_RATE = new Decimal('0.05');
export const MAX_QTY = 99;
export const COUPONS = new Set(['WELCOME10', 'FIXED5', 'FREESHIP']);

const ZERO = new Decimal('0.00');

/**
 * @typedef {object} Item
 * @property {string} product_id
 * @property {number} qty
 */

/**
 * @typedef {object} Line
 * @property {string} product_id
 * @property {number} qty
 * @property {Decimal} unit_price
 * @property {Decimal} total
 */

/**
 * Arrondit un montant au centime (arrondi commercial).
 *
 * @param {Decimal | number | string} value
 * @returns {Decimal}
 */
export function money(value) {
  const d = new Decimal(String(value));
  // Bug injectable pour les démos de régression (MINISHOP_BUG=rounding)
  if (process.env.MINISHOP_BUG === 'rounding') {
    return d.toDecimalPlaces(2, Decimal.ROUND_HALF_EVEN); // arrondi bancaire : 0.125 -> 0.12
  }
  return d.toDecimalPlaces(2, Decimal.ROUND_HALF_UP);
}

/** Devis d'un panier. */
export class Quote {
  /** @param {string | null} [coupon] Code du coupon, déjà normalisé. */
  constructor(coupon = null) {
    /** @type {Line[]} */
    this.lines = [];
    this.subtotal = ZERO;
    this.discount = ZERO;
    this.shipping = ZERO;
    this.total = ZERO;
    this.coupon = coupon;
  }

  /**
   * Représentation sérialisable : les montants deviennent des chaînes à 2 décimales.
   * Appelée automatiquement par JSON.stringify().
   */
  toJSON() {
    return {
      lines: this.lines.map((line) => ({
        product_id: line.product_id,
        qty: line.qty,
        unit_price: line.unit_price.toFixed(2),
        total: line.total.toFixed(2),
      })),
      subtotal: this.subtotal.toFixed(2),
      discount: this.discount.toFixed(2),
      shipping: this.shipping.toFixed(2),
      total: this.total.toFixed(2),
      coupon: this.coupon,
    };
  }
}

/**
 * Total d'une ligne, remise volume incluse.
 *
 * @param {Decimal} unitPrice
 * @param {number} qty
 * @returns {Decimal}
 */
export function lineTotal(unitPrice, qty) {
  if (!Number.isInteger(qty)) {
    throw new TypeError('La quantité doit être un entier');
  }
  if (qty < 1 || qty > MAX_QTY) {
    throw new RangeError(`Quantité hors limites (1..${MAX_QTY}) : ${qty}`);
  }
  let gross = unitPrice.times(qty);
  if (qty >= BULK_QTY) {
    gross = gross.times(new Decimal(1).minus(BULK_RATE));
  }
  return money(gross);
}

/**
 * Montant de la remise apportée par le coupon (positif).
 *
 * @param {Decimal} subtotal
 * @param {string | null} [coupon]
 * @returns {Decimal}
 */
export function couponDiscount(subtotal, coupon) {
  if (coupon === null || coupon === undefined || coupon === '') {
    return ZERO;
  }
  const code = coupon.trim().toUpperCase();
  if (!COUPONS.has(code)) {
    throw new RangeError(`Coupon inconnu : ${coupon}`);
  }
  if (code === 'WELCOME10' && subtotal.greaterThanOrEqualTo('20')) {
    return money(subtotal.times('0.10'));
  }
  if (code === 'FIXED5' && subtotal.greaterThanOrEqualTo('30')) {
    return new Decimal('5.00');
  }
  return ZERO;
}

/**
 * Frais de livraison.
 *
 * @param {Decimal} amountAfterDiscount
 * @param {string | null | undefined} coupon
 * @param {boolean} empty Vrai si le panier est vide.
 * @returns {Decimal}
 */
export function shippingCost(amountAfterDiscount, coupon, empty) {
  if (empty) {
    return ZERO;
  }
  if (coupon && coupon.trim().toUpperCase() === 'FREESHIP') {
    return ZERO;
  }
  if (amountAfterDiscount.greaterThanOrEqualTo(FREE_SHIPPING_THRESHOLD)) {
    return ZERO;
  }
  return SHIPPING_FEE;
}

/**
 * Calcule un devis pour une liste d'items {product_id, qty}.
 *
 * @param {Item[]} items
 * @param {string | null} [coupon]
 * @returns {Quote}
 * @throws {import('./catalog.js').UnknownProductError} si un produit n'existe pas.
 */
export function quote(items, coupon = null) {
  const q = new Quote(coupon ? coupon.trim().toUpperCase() : null);
  for (const item of items) {
    const product = getProduct(item.product_id);
    const total = lineTotal(product.price, item.qty);
    q.lines.push({ product_id: product.id, qty: item.qty, unit_price: product.price, total });
  }
  const empty = q.lines.length === 0;
  q.subtotal = money(q.lines.reduce((sum, line) => sum.plus(line.total), new Decimal(0)));
  q.discount = empty ? ZERO : couponDiscount(q.subtotal, coupon);
  const after = q.subtotal.minus(q.discount);
  q.shipping = shippingCost(after, coupon, empty);
  q.total = money(after.plus(q.shipping));
  return q;
}
