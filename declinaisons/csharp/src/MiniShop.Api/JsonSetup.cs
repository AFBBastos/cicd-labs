using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace MiniShop.Api;

/// <summary>Écrit un montant comme une chaîne à deux décimales (« 27.40 »), quelle que soit la culture du serveur.</summary>
public sealed class MoneyJsonConverter : JsonConverter<decimal>
{
    public override decimal Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options) =>
        reader.TokenType == JsonTokenType.String
            ? decimal.Parse(reader.GetString()!, CultureInfo.InvariantCulture)
            : reader.GetDecimal();

    public override void Write(Utf8JsonWriter writer, decimal value, JsonSerializerOptions options)
    {
        ArgumentNullException.ThrowIfNull(writer);
        writer.WriteStringValue(value.ToString("F2", CultureInfo.InvariantCulture));
    }
}

/// <summary>Réglages JSON communs à toute l'API.</summary>
public static class JsonSetup
{
    public static void Configure(JsonSerializerOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);
        options.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower;   // product_id, unit_price
        options.PropertyNameCaseInsensitive = false;
        options.NumberHandling = JsonNumberHandling.AllowReadingFromString; // "2" accepté pour qty, comme l'original
        options.Converters.Add(new MoneyJsonConverter());
    }
}
