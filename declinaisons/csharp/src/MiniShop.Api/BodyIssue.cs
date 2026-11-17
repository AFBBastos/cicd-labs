using System.Text.Json;
using System.Text.RegularExpressions;

namespace MiniShop.Api;

/// <summary>Traduit une erreur de lecture du corps JSON en problème de validation (emplacement + message).</summary>
public static partial class BodyIssue
{
    public static ValidationIssue From(BadHttpRequestException exception)
    {
        ArgumentNullException.ThrowIfNull(exception);
        if (exception.InnerException is not JsonException json)
        {
            return new ValidationIssue(["body"], "Corps de requête absent ou illisible", "missing");
        }

        var loc = Location(json.Path);
        if (json.Message.Contains("missing required properties", StringComparison.Ordinal))
        {
            return new ValidationIssue(loc, "Champ obligatoire manquant", "missing");
        }

        return json.Path is null or "$" && json.BytePositionInLine > 0 && !json.Message.Contains("could not be converted", StringComparison.Ordinal)
            ? new ValidationIssue(loc, "JSON mal formé", "json_invalid")
            : new ValidationIssue(loc, "Valeur invalide pour ce champ", "invalid_value");
    }

    // « $.items[0].qty » -> ["body", "items", 0, "qty"]
    private static List<object> Location(string? jsonPath)
    {
        List<object> loc = ["body"];
        foreach (Match part in PathPart().Matches(jsonPath ?? string.Empty))
        {
            loc.Add(part.Groups["index"].Success ? int.Parse(part.Groups["index"].Value, System.Globalization.CultureInfo.InvariantCulture) : part.Groups["name"].Value);
        }

        return loc;
    }

    [GeneratedRegex(@"\.(?<name>[^.\[\]]+)|\[(?<index>\d+)\]")]
    private static partial Regex PathPart();
}
