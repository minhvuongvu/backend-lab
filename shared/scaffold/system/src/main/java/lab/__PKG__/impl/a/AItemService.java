package lab.{{PKG}}.impl.a;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import lab.{{PKG}}.contract.ItemService;
import lab.{{PKG}}.domain.Item;

/**
 * Implementation A — wiring example only. Today it behaves exactly like `before`;
 * REPLACE the body with implementation A from 01-research.html §17 and document every step in 03-implementation.html.
 * Add B, C... as sibling packages (impl/b, profile "b") with the same contract.
 */
@Service
@Profile("a")
public class AItemService implements ItemService {

    private final JdbcClient jdbc;

    public AItemService(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    @Transactional
    public Item create(UUID id, String payload) {
        Instant now = Instant.now();
        jdbc.sql("INSERT INTO item (id, payload, created_at) VALUES (:id, :payload, :createdAt)")
                .param("id", id)
                .param("payload", payload)
                .param("createdAt", java.sql.Timestamp.from(now))
                .update();
        return new Item(id, payload, now);
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<Item> find(UUID id) {
        return jdbc.sql("SELECT id, payload, created_at FROM item WHERE id = :id")
                .param("id", id)
                .query((rs, n) -> new Item(rs.getObject("id", UUID.class), rs.getString("payload"),
                        rs.getTimestamp("created_at").toInstant()))
                .optional();
    }

    @Override
    public String implementation() {
        return "a";
    }
}
