/**
 * Tests unitaires des règles de prix — POINT DE DÉPART (Atelier 1).
 *
 * Complétez ce fichier : objectif >= 90 % de couverture de branches sur src/pricing.js.
 */

import Decimal from 'decimal.js';
import { describe, expect, test } from 'vitest';

import { lineTotal, money, quote } from '../../src/pricing.js';

/** Raccourci : D('0.13') construit un montant décimal exact. */
const D = (value) => new Decimal(value);

describe('unit', () => {
  test('money : arrondi commercial', () => {
    // 0.125 s'arrondit à 0.13 (ROUND_HALF_UP), pas 0.12.
    expect(money('0.125')).toEqual(D('0.13'));
  });

  test('lineTotal : sans remise', () => {
    expect(lineTotal(D('12.50'), 2)).toEqual(D('25.00'));
  });

  test('quote : panier vide', () => {
    // Un panier vide coûte 0 € : pas de frais de livraison.
    const q = quote([]);
    expect(q.total).toEqual(D('0.00'));
    expect(q.shipping).toEqual(D('0.00'));
  });
});

// TODO Atelier 1 :
//  - remise volume à partir de 10 unités (et pas à 9 !)
//  - quantités invalides : 0, 100, -1 -> RangeError ; '2', true, 2.5, null -> TypeError   (astuce : test.each)
//  - coupons WELCOME10 / FIXED5 / FREESHIP (seuils inclus/exclus), coupon inconnu, casse
//  - livraison offerte à partir de 50 € APRÈS remise
//  - produit inconnu -> UnknownProductError
