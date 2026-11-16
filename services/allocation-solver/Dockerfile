# Phase 4 allocation solver: fork of TimefoldAI/timefold-quickstarts use-cases/task-assigning (Apache-2.0)
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
RUN mvn -B -q dependency:go-offline || true
COPY src ./src
# Run the constraint unit tests (incl. the Phase 4 capacity constraint), then package.
RUN mvn -B -Dtest=TaskAssigningConstraintProviderTest -Dsurefire.failIfNoSpecifiedTests=false test \
 && mvn -B -DskipTests package

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /src/target/quarkus-app/ /app/
EXPOSE 8080
ENV JAVA_OPTS="-Dquarkus.http.host=0.0.0.0"
CMD ["sh", "-c", "java $JAVA_OPTS -jar /app/quarkus-run.jar"]
