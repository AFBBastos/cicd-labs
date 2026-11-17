<?php

declare(strict_types=1);

namespace MiniShop\Http;

/**
 * Corps JSON d'un panier, validé : {"items": [{"product_id": "mug", "qty": 2}], "coupon": "WELCOME10"}.
 *
 * La validation reproduit celle de la version Python (FastAPI / pydantic) : mêmes tolérances
 * ("2", 2.0 et true sont acceptés comme quantités) et erreurs de même forme
 * ({"type", "loc", "msg", "input"}), renvoyées avec le code 422.
 */
final readonly class CartRequest
{
    private const int MIN_QTY = 1;
    private const int MAX_QTY = 99;

    /**
     * @param list<array{product_id: string, qty: int}> $items
     * @param list<array<string, mixed>>                $errors erreurs de validation (vide si le corps est valide)
     */
    private function __construct(
        public array $items,
        public ?string $coupon,
        public array $errors,
    ) {
    }

    public static function fromJson(string $body): self
    {
        if ('' === trim($body)) {
            return self::invalid(self::error('missing', ['body'], 'Field required', null));
        }
        try {
            $data = json_decode($body, false, 64, \JSON_THROW_ON_ERROR);
        } catch (\JsonException $exception) {
            $error = self::error('json_invalid', ['body', 0], 'JSON decode error', new \stdClass());

            return self::invalid($error + ['ctx' => ['error' => $exception->getMessage()]]);
        }
        if (!$data instanceof \stdClass) {
            $message = 'Input should be a valid dictionary or object to extract fields from';

            return self::invalid(self::error('model_attributes_type', ['body'], $message, $data));
        }

        $errors = [];
        $items = [];
        $rawItems = property_exists($data, 'items') ? $data->items : [];
        if (!\is_array($rawItems)) {
            $errors[] = self::error('list_type', ['body', 'items'], 'Input should be a valid list', $rawItems);
            $rawItems = [];
        }
        foreach (array_values($rawItems) as $index => $rawItem) {
            $item = self::item($rawItem, ['body', 'items', $index], $errors);
            if (null !== $item) {
                $items[] = $item;
            }
        }
        $coupon = $data->coupon ?? null;
        if (null !== $coupon && !\is_string($coupon)) {
            $errors[] = self::error('string_type', ['body', 'coupon'], 'Input should be a valid string', $coupon);
            $coupon = null;
        }

        return new self($items, $coupon, $errors);
    }

    /**
     * @param list<int|string>           $loc
     * @param list<array<string, mixed>> $errors
     *
     * @return array{product_id: string, qty: int}|null
     */
    private static function item(mixed $raw, array $loc, array &$errors): ?array
    {
        if (!$raw instanceof \stdClass) {
            $message = 'Input should be a valid dictionary or object to extract fields from';
            $errors[] = self::error('model_attributes_type', $loc, $message, $raw);

            return null;
        }
        $count = \count($errors);

        $productId = null;
        if (!property_exists($raw, 'product_id')) {
            $errors[] = self::error('missing', [...$loc, 'product_id'], 'Field required', $raw);
        } elseif (!\is_string($raw->product_id)) {
            $message = 'Input should be a valid string';
            $errors[] = self::error('string_type', [...$loc, 'product_id'], $message, $raw->product_id);
        } else {
            $productId = $raw->product_id;
        }

        $qty = null;
        if (!property_exists($raw, 'qty')) {
            $errors[] = self::error('missing', [...$loc, 'qty'], 'Field required', $raw);
        } else {
            $qty = self::quantity($raw->qty, [...$loc, 'qty'], $errors);
        }

        return \count($errors) === $count && null !== $productId && null !== $qty
            ? ['product_id' => $productId, 'qty' => $qty]
            : null;
    }

    /**
     * @param list<int|string>           $loc
     * @param list<array<string, mixed>> $errors
     */
    private static function quantity(mixed $raw, array $loc, array &$errors): ?int
    {
        if (\is_bool($raw)) {
            $value = (float) $raw;
        } elseif (\is_int($raw)) {
            $value = (float) $raw;
        } elseif (\is_float($raw)) {
            if (floor($raw) !== $raw) {
                $message = 'Input should be a valid integer, got a number with a fractional part';
                $errors[] = self::error('int_from_float', $loc, $message, is_finite($raw) ? $raw : null);

                return null;
            }
            $value = $raw;
        } elseif (\is_string($raw) && 1 === preg_match('/^\s*[+-]?\d{1,18}\s*$/', $raw)) {
            $value = (float) trim($raw);
        } elseif (\is_string($raw)) {
            $message = 'Input should be a valid integer, unable to parse string as an integer';
            $errors[] = self::error('int_parsing', $loc, $message, $raw);

            return null;
        } else {
            $errors[] = self::error('int_type', $loc, 'Input should be a valid integer', $raw);

            return null;
        }

        if ($value < self::MIN_QTY) {
            $message = 'Input should be greater than or equal to '.self::MIN_QTY;
            $errors[] = self::error('greater_than_equal', $loc, $message, $raw) + ['ctx' => ['ge' => self::MIN_QTY]];

            return null;
        }
        if ($value > self::MAX_QTY) {
            $message = 'Input should be less than or equal to '.self::MAX_QTY;
            $errors[] = self::error('less_than_equal', $loc, $message, $raw) + ['ctx' => ['le' => self::MAX_QTY]];

            return null;
        }

        return (int) $value;
    }

    /**
     * @param list<int|string> $loc
     *
     * @return array<string, mixed>
     */
    private static function error(string $type, array $loc, string $message, mixed $input): array
    {
        return ['type' => $type, 'loc' => $loc, 'msg' => $message, 'input' => $input];
    }

    /** @param array<string, mixed> $error */
    private static function invalid(array $error): self
    {
        return new self([], null, [$error]);
    }
}
