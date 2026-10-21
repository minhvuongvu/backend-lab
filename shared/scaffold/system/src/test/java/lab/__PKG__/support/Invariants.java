package lab.{{PKG}}.support;

import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Invariant helpers shared by tests and mirrored by experiments/checker/integrity_check.py.
 * Example invariant: every id that was acknowledged to the client exists exactly once in the store.
 */
public final class Invariants {

    private Invariants() {
    }

    public record ExactlyOnceReport(List<UUID> missing, Map<UUID, Long> duplicated) {
        public boolean holds() {
            return missing.isEmpty() && duplicated.isEmpty();
        }
    }

    /** Compares ids acknowledged to clients with ids found in the store (stored may contain duplicates). */
    public static ExactlyOnceReport exactlyOnce(Collection<UUID> acknowledged, Collection<UUID> stored) {
        Map<UUID, Long> counts = new HashMap<>();
        stored.forEach(id -> counts.merge(id, 1L, Long::sum));
        List<UUID> missing = acknowledged.stream().filter(id -> !counts.containsKey(id)).toList();
        Map<UUID, Long> duplicated = new HashMap<>();
        counts.forEach((id, n) -> {
            if (n > 1) {
                duplicated.put(id, n);
            }
        });
        return new ExactlyOnceReport(missing, duplicated);
    }
}
