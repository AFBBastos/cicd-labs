# Image de l'application MiniShop (C# / ASP.NET Core). Contexte de construction : declinaisons/csharp
#   docker build -t minishop-csharp .

# --- Étape 1 : compilation et publication (SDK complet, absent de l'image finale)
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
# D'abord les seuls fichiers qui décrivent les dépendances : la couche « restore » reste en cache
# tant qu'ils ne changent pas.
COPY Directory.Build.props .editorconfig ./
COPY src/MiniShop/MiniShop.csproj src/MiniShop/packages.lock.json src/MiniShop/
COPY src/MiniShop.Api/MiniShop.Api.csproj src/MiniShop.Api/packages.lock.json src/MiniShop.Api/
RUN dotnet restore src/MiniShop.Api --locked-mode
COPY src/ src/
RUN dotnet publish src/MiniShop.Api --no-restore -c Release -o /app

# --- Étape 2 : exécution (runtime ASP.NET seul)
FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
# Correctifs de sécurité Ubuntu publiés depuis la construction de l'image de base (cf. Trivy, Atelier 11) ;
# curl ne sert qu'au HEALTHCHECK.
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /app .
ENV ASPNETCORE_HTTP_PORTS=8000
USER $APP_UID
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s CMD curl -sf http://localhost:8000/health || exit 1
ENTRYPOINT ["dotnet", "MiniShop.Api.dll"]
