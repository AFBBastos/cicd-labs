// Test E2E Playwright — POINT DE DÉPART (Atelier 8).
//
// Prérequis : application lancée (docker compose up -d --build à la racine du dépôt) ;
//             BASE_URL=http://localhost:8000 par défaut.
// Lancer :    dotnet test --filter "Category=e2e"          (HEADED=1 pour voir le navigateur)

using System.Text.RegularExpressions;
using Microsoft.Playwright.Xunit;

namespace MiniShop.Acceptance.Tests;

[Trait("Category", "e2e")]
public class ParcoursAchatTests : PageTest
{
    [Fact]
    public async Task Page_accueil()
    {
        await Page.GotoAsync(AppUrl.Value);

        await Expect(Page).ToHaveTitleAsync(new Regex("MiniShop"));
        await Expect(Page.GetByTestId("products").Locator("li")).ToHaveCountAsync(5);
    }

    // TODO Atelier 8 : ajouter 2 mugs, appliquer WELCOME10, vérifier le total, commander.
}
