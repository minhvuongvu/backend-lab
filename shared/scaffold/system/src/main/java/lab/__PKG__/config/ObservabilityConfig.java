package lab.{{PKG}}.config;

import io.micrometer.core.instrument.MeterRegistry;

import org.springframework.beans.factory.annotation.Value;
// Boot 4: moved from org.springframework.boot.actuate.autoconfigure.metrics (module spring-boot-micrometer-metrics).
import org.springframework.boot.micrometer.metrics.autoconfigure.MeterRegistryCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Tags every metric with topic + implementation so before/A/B series are separable in Prometheus and in
 * scripts/prom_export.py exports. `lab.impl` comes from the profile file (application-<impl>.yml), not from
 * the ItemService bean, so the meter registry does not depend on the data layer during startup.
 */
@Configuration
public class ObservabilityConfig {

    @Bean
    MeterRegistryCustomizer<MeterRegistry> labTags(@Value("${lab.topic}") String topic, @Value("${lab.impl}") String impl) {
        return registry -> registry.config().commonTags("topic", topic, "impl", impl);
    }
}
