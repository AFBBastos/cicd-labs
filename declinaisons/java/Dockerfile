# Étape 1 — construction : Maven et le JDK ne servent qu'ici, ils ne partent pas en production
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
COPY src ./src
RUN mvn -B -ntp -DskipTests package

# Étape 2 — exécution : JRE seul, sur une base légère
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
# Correctifs de sécurité Alpine publiés depuis la construction de l'image de base (cf. Trivy, Atelier 11)
RUN apk upgrade --no-cache
RUN adduser -D appuser
COPY --from=build /src/target/minishop.jar ./minishop.jar
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s CMD wget -q -O /dev/null http://localhost:8000/health || exit 1
CMD ["java", "-jar", "minishop.jar"]
