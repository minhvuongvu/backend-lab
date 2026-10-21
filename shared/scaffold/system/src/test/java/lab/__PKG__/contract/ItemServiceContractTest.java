package lab.{{PKG}}.contract;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.simple.JdbcClient;

import lab.{{PKG}}.support.AbstractIntegrationTest;
import lab.{{PKG}}.support.Invariants;

/**
 * Contract tests run unchanged against every implementation: one concrete subclass per profile
 * (BeforeContractTest, AContractTest, ...). Topic-specific failure tests (crash, retry, concurrency)
 * go here too so every implementation is held to the same invariants (01-research.html §9–10).
 * A test that `before` is EXPECTED to fail (it demonstrates the problem) is overridden in BeforeContractTest
 * with an assertion of the failure, and the reason is written in 03-implementation.html.
 */
public abstract class ItemServiceContractTest extends AbstractIntegrationTest {

    @Autowired
    protected ItemService service;

    @Autowired
    protected JdbcClient jdbc;

    protected abstract String expectedImplementation();

    @Test
    void activeImplementationMatchesProfile() {
        assertThat(service.implementation()).isEqualTo(expectedImplementation());
    }

    @Test
    void createdItemCanBeRead() {
        UUID id = UUID.randomUUID();
        service.create(id, "hello");
        assertThat(service.find(id)).get().extracting(item -> item.payload()).isEqualTo("hello");
    }

    @Test
    void everyAcknowledgedIdIsStoredExactlyOnce() {
        List<UUID> acknowledged = new ArrayList<>();
        for (int i = 0; i < 50; i++) {
            UUID id = UUID.randomUUID();
            service.create(id, "p" + i);
            acknowledged.add(id);
        }
        List<UUID> stored = jdbc.sql("SELECT id FROM item").query(UUID.class).list();
        Invariants.ExactlyOnceReport report = Invariants.exactlyOnce(acknowledged, stored);
        assertThat(report.holds()).as("missing=%s duplicated=%s", report.missing(), report.duplicated()).isTrue();
    }
}
