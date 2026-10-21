# Multi-stage build; the runtime image only contains the JRE and the layered application.
# Build context: this directory (experiments/docker-compose.yml uses `build: ../system`).
FROM eclipse-temurin:21.0.8_9-jdk AS build
WORKDIR /src
COPY .mvn .mvn
COPY mvnw pom.xml ./
RUN chmod +x mvnw && ./mvnw -q -B dependency:go-offline
COPY src src
RUN ./mvnw -q -B -DskipTests package \
 && java -Djarmode=tools -jar target/*.jar extract --layers --launcher --destination /extracted

FROM eclipse-temurin:21.0.8_9-jre
WORKDIR /app
# Layers ordered from least to most frequently changed so rebuilds reuse cached layers.
COPY --from=build /extracted/dependencies/ ./
COPY --from=build /extracted/spring-boot-loader/ ./
COPY --from=build /extracted/snapshot-dependencies/ ./
COPY --from=build /extracted/application/ ./
# The container has cpus/mem_limit set by docker-compose (identical for every implementation).
# MaxRAMPercentage sizes the heap from the cgroup memory limit instead of host RAM; 75% leaves room for
# metaspace, thread stacks, direct buffers and the code cache. The JVM also derives GC/JIT thread counts
# from the cgroup CPU quota, so the same limits give every implementation the same JVM shape.
ENV JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=75 -XX:+ExitOnOutOfMemoryError"
EXPOSE 8080
ENTRYPOINT ["java", "org.springframework.boot.loader.launch.JarLauncher"]
