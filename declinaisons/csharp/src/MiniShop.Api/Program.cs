// API HTTP MiniShop (ASP.NET Core, API minimale).
//
// Lancer :  dotnet run --project src/MiniShop.Api          (http://localhost:8000)
// Docs   :  http://localhost:8000/docs   (OpenAPI : /openapi.json)

using System.Collections.Concurrent;
using System.Reflection;
using Microsoft.AspNetCore.Http.Json;
using Microsoft.OpenApi;
using MiniShop;
using MiniShop.Api;
using Prometheus;

var version = Assembly.GetExecutingAssembly().GetName().Version?.ToString(3) ?? "0.0.0";

var builder = WebApplication.CreateBuilder(args);
builder.Services.Configure<JsonOptions>(o => JsonSetup.Configure(o.SerializerOptions));
// Un corps illisible lève une exception (traitée plus bas en 422) au lieu d'un 400 muet.
builder.Services.Configure<RouteHandlerOptions>(o => o.ThrowOnBadRequest = true);
builder.Services.AddSingleton(new RequestLog(Environment.GetEnvironmentVariable("MINISHOP_LOG_FILE")));
builder.Services.AddOpenApi(options =>
{
    options.AddDocumentTransformer((document, _, _) =>
    {
        document.Info = new OpenApiInfo
        {
            Title = "MiniShop",
            Version = version,
            Description = "Application fil rouge de la formation CI/CD & IA",
        };
        return Task.CompletedTask;
    });
    // Les montants sont des decimal côté C#, mais des chaînes « 12.50 » dans le JSON : le schéma doit le dire.
    options.AddSchemaTransformer((schema, context, _) =>
    {
        if (context.JsonTypeInfo.Type == typeof(decimal))
        {
            schema.Type = JsonSchemaType.String;
            schema.Format = null;
            schema.Pattern = @"^-?\d+\.\d{2}$";
        }

        return Task.CompletedTask;
    });
});

var app = builder.Build();

app.UseMiddleware<ObserveMiddleware>();

// Réponses d'erreur sans corps produites par le cadriciel (route inconnue, méthode refusée, type de contenu
// refusé) : on leur donne un champ « detail », comme le reste de l'API.
app.UseStatusCodePages(async statusContext =>
{
    var response = statusContext.HttpContext.Response;
    if (response.StatusCode == StatusCodes.Status415UnsupportedMediaType)
    {
        response.StatusCode = StatusCodes.Status422UnprocessableEntity;
        var issue = new ValidationIssue(["body"], "Le corps doit être un objet JSON (Content-Type: application/json)", "invalid_content_type");
        await response.WriteAsJsonAsync(new ValidationErrorResponse([issue]));
        return;
    }

    var detail = response.StatusCode switch
    {
        StatusCodes.Status404NotFound => "Not Found",
        StatusCodes.Status405MethodNotAllowed => "Method Not Allowed",
        _ => $"Erreur {response.StatusCode}",
    };
    await response.WriteAsJsonAsync(new ErrorResponse(detail));
});

// Corps de requête invalide (JSON mal formé, champ manquant, mauvais type) : 422 et un champ « detail ».
app.Use(async (context, next) =>
{
    try
    {
        await next(context);
    }
    catch (BadHttpRequestException exc) when (!context.Response.HasStarted)
    {
        await Results.Json(
                new ValidationErrorResponse([BodyIssue.From(exc)]),
                statusCode: StatusCodes.Status422UnprocessableEntity)
            .ExecuteAsync(context);
    }
});

app.UseStaticFiles(); // wwwroot/static/* -> /static/*

var orders = new ConcurrentDictionary<string, OrderResponse>();

app.MapGet("/", (IWebHostEnvironment env) =>
        Results.File(Path.Combine(env.WebRootPath, "static", "index.html"), "text/html; charset=utf-8"))
    .ExcludeFromDescription();

app.MapGet("/health", () => new HealthResponse("ok", version))
    .WithSummary("Health");

app.MapGet("/metrics", async (HttpContext context) =>
    {
        context.Response.ContentType = PrometheusConstants.TextContentTypeWithVersionAndEncoding;
        await Metrics.DefaultRegistry.CollectAndExportAsTextAsync(context.Response.Body, context.RequestAborted);
    })
    .ExcludeFromDescription();

app.MapGet("/products", () => Catalog.ListProducts())
    .WithSummary("Products");

app.MapGet("/products/{product_id}", IResult (string product_id) =>
    {
        try
        {
            return Results.Ok(Catalog.GetProduct(product_id));
        }
        catch (KeyNotFoundException exc)
        {
            return Results.NotFound(new ErrorResponse(exc.Message));
        }
    })
    .WithSummary("Product")
    .Produces<Product>()
    .Produces<ErrorResponse>(StatusCodes.Status404NotFound);

app.MapPost("/cart/quote", IResult (CartRequest cart) =>
        ComputeQuote(cart, out var quote) is { } error ? error : Results.Ok(quote))
    .WithSummary("Cart Quote")
    .Produces<Quote>()
    .Produces<ErrorResponse>(StatusCodes.Status404NotFound)
    .Produces<UnprocessableResponse>(StatusCodes.Status422UnprocessableEntity);

app.MapPost("/orders", IResult (CartRequest cart) =>
    {
        if (Validate(cart) is { } invalid)
        {
            return invalid;
        }

        if (cart.Items.Count == 0)
        {
            return Unprocessable("Panier vide");
        }

        if (ComputeQuote(cart, out var q) is { } error)
        {
            return error;
        }

        var id = Guid.NewGuid().ToString("N")[..12];
        var order = new OrderResponse(id, q!.Lines, q.Subtotal, q.Discount, q.Shipping, q.Total, q.Coupon);
        orders[id] = order;
        AppMetrics.Orders.Inc();
        return Results.Json(order, statusCode: StatusCodes.Status201Created);
    })
    .WithSummary("Create Order")
    .Produces<OrderResponse>(StatusCodes.Status201Created)
    .Produces<ErrorResponse>(StatusCodes.Status404NotFound)
    .Produces<UnprocessableResponse>(StatusCodes.Status422UnprocessableEntity);

app.MapGet("/orders/{order_id}", IResult (string order_id) =>
        orders.TryGetValue(order_id, out var order)
            ? Results.Ok(order)
            : Results.NotFound(new ErrorResponse("Commande introuvable")))
    .WithSummary("Get Order")
    .Produces<OrderResponse>()
    .Produces<ErrorResponse>(StatusCodes.Status404NotFound);

app.MapOpenApi("/openapi.json");
app.UseSwaggerUI(options =>
{
    options.RoutePrefix = "docs";
    options.SwaggerEndpoint("/openapi.json", "MiniShop");
    options.DocumentTitle = "MiniShop - Swagger UI";
});

app.Run();

static IResult Unprocessable(string detail) =>
    Results.Json(new ErrorResponse(detail), statusCode: StatusCodes.Status422UnprocessableEntity);

// Validation du corps, comme le modèle Pydantic de l'original : une liste d'articles, quantité entre 1 et 99.
// Renvoie la réponse 422 à émettre, ou null si le panier est valide.
static IResult? Validate(CartRequest cart)
{
    List<ValidationIssue> issues = [];
    if (cart.Items is null)
    {
        issues.Add(new ValidationIssue(["body", "items"], "Input should be a valid list", "list_type"));
    }
    else
    {
        for (var index = 0; index < cart.Items.Count; index++)
        {
            var item = cart.Items[index];
            if (item is null)
            {
                issues.Add(new ValidationIssue(["body", "items", index], "Input should be a valid object", "model_type"));
            }
            else if (item.ProductId is null)
            {
                issues.Add(new ValidationIssue(["body", "items", index, "product_id"], "Input should be a valid string", "string_type"));
            }
            else if (item.Qty < 1)
            {
                issues.Add(new ValidationIssue(["body", "items", index, "qty"], "Input should be greater than or equal to 1", "greater_than_equal"));
            }
            else if (item.Qty > Pricing.MaxQty)
            {
                issues.Add(new ValidationIssue(["body", "items", index, "qty"], $"Input should be less than or equal to {Pricing.MaxQty}", "less_than_equal"));
            }
        }
    }

    return issues.Count == 0
        ? null
        : Results.Json(new ValidationErrorResponse(issues), statusCode: StatusCodes.Status422UnprocessableEntity);
}

// Calcule le devis ; en cas d'erreur, renvoie la réponse HTTP correspondante (404 ou 422) et quote vaut null.
static IResult? ComputeQuote(CartRequest cart, out Quote? quote)
{
    quote = null;
    if (Validate(cart) is { } invalid)
    {
        return invalid;
    }

    try
    {
        quote = Pricing.Quote(cart.Items.Select(i => new CartItem(i.ProductId, i.Qty)), cart.Coupon);
        return null;
    }
    catch (KeyNotFoundException exc)
    {
        return Results.NotFound(new ErrorResponse(exc.Message));
    }
    catch (ArgumentException exc)
    {
        return Unprocessable(exc.Message);
    }
}
