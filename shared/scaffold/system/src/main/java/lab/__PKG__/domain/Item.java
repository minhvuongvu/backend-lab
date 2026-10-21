package lab.{{PKG}}.domain;

import java.time.Instant;
import java.util.UUID;

/**
 * Example domain object. REPLACE with the topic's minimal domain (02-system-design.html §1).
 */
public record Item(UUID id, String payload, Instant createdAt) {
}
