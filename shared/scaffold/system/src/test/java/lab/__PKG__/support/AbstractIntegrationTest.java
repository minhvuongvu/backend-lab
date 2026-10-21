package lab.{{PKG}}.support;

import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.testcontainers.containers.PostgreSQLContainer;

/**
 * Real infrastructure in containers (no mocks for the parts the topic is about).
 *
 * Singleton-container pattern: containers start once per JVM and are never stopped by JUnit.
 * Why not @Testcontainers + static @Container: that stops the container after each test class, while
 * Spring caches the application context across classes (e.g. BeforeContractTest, AContractTest) and the
 * cached context would keep pointing at a dead port. Ryuk removes the containers when the JVM exits.
 * Pin the image to the same version as experiments/docker-compose.yml.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public abstract class AbstractIntegrationTest {

    @ServiceConnection
    static final PostgreSQLContainer<?> POSTGRES = new PostgreSQLContainer<>("postgres:17.6-alpine");

    // Enable when the topic uses Kafka / Redis (and the matching dependencies in pom.xml), and start them below:
    // @ServiceConnection
    // static final org.testcontainers.kafka.KafkaContainer KAFKA = new org.testcontainers.kafka.KafkaContainer("apache/kafka:4.1.0");
    // @ServiceConnection(name = "redis")
    // static final org.testcontainers.containers.GenericContainer<?> REDIS =
    //         new org.testcontainers.containers.GenericContainer<>("redis:8.2.2-alpine").withExposedPorts(6379);

    static {
        POSTGRES.start();
    }
}
