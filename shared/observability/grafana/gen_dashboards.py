"""Generate the provisioned Grafana dashboards (JVM/HTTP/k6, Containers, Datastores, Traces).

Edit this file, then regenerate instead of hand-editing the JSON:
    python3 shared/observability/grafana/gen_dashboards.py shared/observability/grafana/dashboards
Grafana reloads the folder every 30s.
"""
import json, os, sys

OUT = sys.argv[1]
DS = {"type": "prometheus", "uid": "prometheus"}


class Dash:
    def __init__(self):
        self.panels = []
        self.y = 0
        self.x = 0
        self.id = 0
        self.row_h = 0

    def _nid(self):
        self.id += 1
        return self.id

    def row(self, title):
        if self.x:
            self.y += self.row_h
            self.x = 0
        self.panels.append({"id": self._nid(), "type": "row", "title": title, "collapsed": False,
                            "gridPos": {"x": 0, "y": self.y, "w": 24, "h": 1}, "panels": []})
        self.y += 1
        self.row_h = 0

    def _place(self, w, h):
        if self.x + w > 24:
            self.y += self.row_h
            self.x = 0
            self.row_h = 0
        pos = {"x": self.x, "y": self.y, "w": w, "h": h}
        self.x += w
        self.row_h = max(self.row_h, h)
        return pos

    def ts(self, title, targets, unit="short", w=12, h=8, desc="", stack=False, overrides=None, minv=None, maxv=None):
        custom = {"lineWidth": 1, "fillOpacity": 10, "showPoints": "never"}
        if stack:
            custom["stacking"] = {"mode": "normal"}
        defaults = {"unit": unit, "custom": custom}
        if minv is not None:
            defaults["min"] = minv
        if maxv is not None:
            defaults["max"] = maxv
        self.panels.append({
            "id": self._nid(), "type": "timeseries", "title": title, "description": desc, "datasource": DS,
            "gridPos": self._place(w, h),
            "fieldConfig": {"defaults": defaults, "overrides": overrides or []},
            "options": {"legend": {"displayMode": "table", "placement": "bottom", "calcs": ["mean", "max", "lastNotNull"]},
                        "tooltip": {"mode": "multi", "sort": "desc"}},
            "targets": [{"refId": chr(65 + i), "datasource": DS, "expr": e, "legendFormat": l} for i, (e, l) in enumerate(targets)],
        })

    def stat(self, title, targets, unit="short", w=6, h=4, desc="", thresholds=None, mappings=None, color_mode="value"):
        self.panels.append({
            "id": self._nid(), "type": "stat", "title": title, "description": desc, "datasource": DS,
            "gridPos": self._place(w, h),
            "fieldConfig": {"defaults": {"unit": unit, "mappings": mappings or [],
                                         "thresholds": thresholds or {"mode": "absolute", "steps": [{"color": "green", "value": None}]}},
                            "overrides": []},
            "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                        "colorMode": color_mode, "graphMode": "area", "textMode": "value_and_name", "justifyMode": "auto"},
            "targets": [{"refId": chr(65 + i), "datasource": DS, "expr": e, "legendFormat": l, "instant": False} for i, (e, l) in enumerate(targets)],
        })

    def text(self, title, content, w=24, h=4):
        self.panels.append({"id": self._nid(), "type": "text", "title": title, "gridPos": self._place(w, h),
                            "options": {"mode": "markdown", "content": content}})

    def build(self, uid, title, templating=None, links=None):
        return {
            "uid": uid, "title": title, "tags": ["backend-lab"], "timezone": "browser", "schemaVersion": 39,
            "version": 1, "editable": True, "refresh": "5s", "time": {"from": "now-15m", "to": "now"},
            "templating": {"list": templating or []}, "annotations": {"list": []}, "links": links or [],
            "panels": self.panels,
        }


def var(name, query, label=None, multi=True, include_all=True):
    return {"name": name, "label": label or name, "type": "query", "datasource": DS,
            "query": {"query": query, "refId": name}, "definition": query,
            "includeAll": include_all, "multi": multi, "allValue": ".*",
            "current": {"selected": True, "text": ["All"], "value": ["$__all"]}, "refresh": 2, "sort": 1}


LINKS = [{"title": "backend-lab", "type": "dashboards", "tags": ["backend-lab"], "asDropdown": True, "includeVars": False, "keepTime": True}]
RED_GREEN = {"mode": "absolute", "steps": [{"color": "red", "value": None}, {"color": "green", "value": 1}]}
GREEN_RED = {"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "red", "value": 1}]}
UP_MAP = [{"type": "value", "options": {"0": {"text": "DOWN", "color": "red"}, "1": {"text": "UP", "color": "green"}}}]


# ------------------------------------------------------------------ containers
def containers():
    d = Dash()
    S = 'compose_project=~"$compose_project", container=~"$container"'
    d.row("Resources per container")
    d.ts("CPU used (cores)", [(f'rate(lab_container_cpu_usage_seconds_total{{{S}}}[$__rate_interval])', "{{container}}")],
         "short", desc="CPU cores consumed (1.0 = one full core). Source: Docker Engine API via docker-stats exporter.")
    d.ts("CPU used vs limit", [(f'rate(lab_container_cpu_usage_seconds_total{{{S}}}[$__rate_interval]) / (lab_container_cpu_limit_cores{{{S}}} > 0)', "{{container}}")],
         "percentunit", desc="Only containers with a CPU limit. Sustained values near 100% mean the container is CPU-bound by its limit.",
         minv=0)
    d.ts("CPU throttling ratio", [(f'rate(lab_container_cpu_throttled_periods_total{{{S}}}[$__rate_interval]) / (rate(lab_container_cpu_periods_total{{{S}}}[$__rate_interval]) > 0)', "{{container}}")],
         "percentunit",
         desc="Share of CFS periods in which the container was throttled. ANY sustained throttling distorts latency results "
              "(p99 jumps by up to one CFS period, 100ms by default) even when average CPU looks low. "
              "Check this before trusting a latency comparison between implementations.",
         minv=0, maxv=1)
    d.ts("Throttled time / s", [(f'rate(lab_container_cpu_throttled_seconds_total{{{S}}}[$__rate_interval])', "{{container}}")],
         "s", desc="Seconds per second the container spent throttled.")
    d.ts("Memory used", [(f'lab_container_memory_usage_bytes{{{S}}}', "{{container}}")], "bytes",
         desc="Usage excluding inactive page cache — same number as `docker stats`.")
    d.ts("Memory used vs limit", [(f'lab_container_memory_usage_bytes{{{S}}} / lab_container_memory_limit_bytes{{{S}}}', "{{container}}")],
         "percentunit", desc="Close to 100% → risk of OOM kill (see stat panels below). Containers without a limit are measured against the Docker VM's total memory.",
         minv=0, maxv=1)
    d.ts("Network receive", [(f'rate(lab_container_network_receive_bytes_total{{{S}}}[$__rate_interval])', "{{container}}")], "Bps")
    d.ts("Network transmit", [(f'rate(lab_container_network_transmit_bytes_total{{{S}}}[$__rate_interval])', "{{container}}")], "Bps")
    d.ts("Block IO read", [(f'rate(lab_container_blkio_read_bytes_total{{{S}}}[$__rate_interval])', "{{container}}")], "Bps")
    d.ts("Block IO write", [(f'rate(lab_container_blkio_write_bytes_total{{{S}}}[$__rate_interval])', "{{container}}")], "Bps",
         desc="Includes WAL/fsync traffic of databases and brokers.")
    d.ts("Processes / threads", [(f'lab_container_pids{{{S}}}', "{{container}}")], "short", w=8)
    d.stat("Restarts", [(f'lab_container_restart_count{{{S}}}', "{{container}}")], w=8,
           thresholds=GREEN_RED, desc="Docker restart count. Non-zero during an experiment invalidates that run.")
    d.stat("OOM killed", [(f'lab_container_oom_killed{{{S}}}', "{{container}}")], w=8,
           thresholds=GREEN_RED, desc="1 if the container's last exit was an OOM kill.")

    O = 'compose_project="backend-lab-obs"'
    d.row("Observability overhead (backend-lab-obs)")
    d.text("Why this matters",
           "The observability stack runs on the same machine as the experiment. Its CPU/memory is a **confounding variable**: "
           "keep the same stack (same `OBS` mode, same tracing sampling) for `before` and every implementation, and report it in `results/env.md`.",
           h=3)
    d.ts("Obs stack CPU (cores)", [(f'sum(rate(lab_container_cpu_usage_seconds_total{{{O}}}[$__rate_interval]))', "total"),
                                   (f'rate(lab_container_cpu_usage_seconds_total{{{O}}}[$__rate_interval])', "{{compose_service}}")],
         "short", stack=False)
    d.ts("Obs stack memory", [(f'sum(lab_container_memory_usage_bytes{{{O}}})', "total"),
                              (f'lab_container_memory_usage_bytes{{{O}}}', "{{compose_service}}")], "bytes")
    d.stat("docker-stats collect loop", [("lab_docker_stats_collect_seconds", "loop duration")], "s", w=12,
           desc="Time to collect stats for all lab containers. Should stay well below the 5s interval.")
    d.stat("docker-stats errors", [("lab_docker_stats_errors", "errors")], w=12, thresholds=GREEN_RED)

    tmpl = [
        var("compose_project", "label_values(lab_container_memory_usage_bytes, compose_project)", "Compose project"),
        var("container", 'label_values(lab_container_memory_usage_bytes{compose_project=~"$compose_project"}, container)', "Container"),
    ]
    return d.build("backend-lab-containers", "backend-lab — Containers", tmpl, LINKS)


# ------------------------------------------------------------------ datastores
def datastores():
    d = Dash()
    P = 'compose_project=~"$compose_project"'
    d.row("PostgreSQL (postgres-exporter)")
    d.stat("PostgreSQL", [(f'pg_up{{{P}}}', "{{compose_project}}")], w=4, thresholds=RED_GREEN, mappings=UP_MAP, color_mode="background")
    d.stat("Backends", [(f'sum by (compose_project) (pg_stat_database_numbackends{{{P}}})', "{{compose_project}}")], w=4)
    d.stat("Longest transaction", [(f'max by (compose_project) (pg_stat_activity_max_tx_duration{{{P}}})', "{{compose_project}}")], "s", w=4,
           desc="Long transactions hold snapshots/locks and block vacuum; a classic cause of tail latency.",
           thresholds={"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "orange", "value": 5}, {"color": "red", "value": 30}]})
    d.stat("Deadlocks (range)", [(f'sum by (compose_project) (increase(pg_stat_database_deadlocks{{{P}}}[$__range]))', "{{compose_project}}")], w=4, thresholds=GREEN_RED)
    d.stat("Cache hit ratio", [(f'sum by (compose_project) (rate(pg_stat_database_blks_hit{{{P}}}[$__rate_interval])) / (sum by (compose_project) (rate(pg_stat_database_blks_hit{{{P}}}[$__rate_interval])) + sum by (compose_project) (rate(pg_stat_database_blks_read{{{P}}}[$__rate_interval])))', "{{compose_project}}")],
           "percentunit", w=8, desc="shared_buffers hit ratio. A cold cache in one run but not another skews comparisons — warm up first.",
           thresholds={"mode": "absolute", "steps": [{"color": "red", "value": None}, {"color": "orange", "value": 0.9}, {"color": "green", "value": 0.99}]})
    d.ts("Connections by state", [(f'sum by (state) (pg_stat_activity_count{{{P}}})', "{{state}}")], "short",
         desc="'idle in transaction' > 0 for long = app holding a transaction open (e.g. waiting on a remote call inside @Transactional).")
    d.ts("Transactions / s", [(f'sum(rate(pg_stat_database_xact_commit{{{P}}}[$__rate_interval]))', "commit"),
                              (f'sum(rate(pg_stat_database_xact_rollback{{{P}}}[$__rate_interval]))', "rollback")], "ops")
    d.ts("Tuples / s", [(f'sum(rate(pg_stat_database_tup_inserted{{{P}}}[$__rate_interval]))', "inserted"),
                        (f'sum(rate(pg_stat_database_tup_updated{{{P}}}[$__rate_interval]))', "updated"),
                        (f'sum(rate(pg_stat_database_tup_deleted{{{P}}}[$__rate_interval]))', "deleted"),
                        (f'sum(rate(pg_stat_database_tup_fetched{{{P}}}[$__rate_interval]))', "fetched")], "ops")
    d.ts("Locks by mode", [(f'sum by (mode) (pg_locks_count{{{P}}})', "{{mode}}")], "short")
    d.ts("Temp files written", [(f'sum(rate(pg_stat_database_temp_bytes{{{P}}}[$__rate_interval]))', "temp bytes/s")], "Bps",
         desc="Sorts/hashes spilling to disk because work_mem is too small.")
    d.ts("Database size", [(f'sum by (datname) (pg_database_size_bytes{{{P}}})', "{{datname}}")], "bytes")

    d.row("Redis (redis_exporter)")
    d.stat("Redis", [(f'redis_up{{{P}}}', "{{compose_project}}")], w=4, thresholds=RED_GREEN, mappings=UP_MAP, color_mode="background")
    d.stat("Clients", [(f'redis_connected_clients{{{P}}}', "{{compose_project}}")], w=4)
    d.stat("Keys", [(f'sum by (compose_project) (redis_db_keys{{{P}}})', "{{compose_project}}")], w=4)
    d.stat("Hit ratio", [(f'sum by (compose_project) (rate(redis_keyspace_hits_total{{{P}}}[$__rate_interval])) / (sum by (compose_project) (rate(redis_keyspace_hits_total{{{P}}}[$__rate_interval])) + sum by (compose_project) (rate(redis_keyspace_misses_total{{{P}}}[$__rate_interval])))', "{{compose_project}}")],
           "percentunit", w=6)
    d.stat("Evicted keys (range)", [(f'sum by (compose_project) (increase(redis_evicted_keys_total{{{P}}}[$__range]))', "{{compose_project}}")], w=6, thresholds=GREEN_RED,
           desc="Evictions mean maxmemory was reached: cache results stop being comparable.")
    d.ts("Commands / s", [(f'sum by (compose_project) (rate(redis_commands_processed_total{{{P}}}[$__rate_interval]))', "{{compose_project}}")], "ops")
    d.ts("Mean latency by command", [(f'sum by (cmd) (rate(redis_commands_duration_seconds_total{{{P}}}[$__rate_interval])) / sum by (cmd) (rate(redis_commands_total{{{P}}}[$__rate_interval]))', "{{cmd}}")], "s",
         desc="Server-side execution time only — excludes network and client queueing.")
    d.ts("Memory used vs max", [(f'redis_memory_used_bytes{{{P}}}', "used"), (f'redis_memory_max_bytes{{{P}}} > 0', "maxmemory")], "bytes",
         desc="maxmemory = 0 (not shown) means unlimited.")
    d.ts("Expired / evicted keys / s", [(f'sum(rate(redis_expired_keys_total{{{P}}}[$__rate_interval]))', "expired"),
                                        (f'sum(rate(redis_evicted_keys_total{{{P}}}[$__rate_interval]))', "evicted")], "ops")

    d.row("Kafka (kafka-exporter)")
    d.stat("Brokers", [(f'kafka_brokers{{{P}}}', "{{compose_project}}")], w=6)
    d.stat("Partitions", [(f'sum by (compose_project) (kafka_topic_partitions{{{P}}})', "{{compose_project}}")], w=6)
    d.stat("Total consumer lag", [(f'sum by (compose_project) (kafka_consumergroup_lag{{{P}}})', "{{compose_project}}")], w=6,
           thresholds={"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "orange", "value": 100}, {"color": "red", "value": 1000}]})
    d.stat("Under-replicated partitions", [(f'sum by (compose_project) (kafka_topic_partition_under_replicated_partition{{{P}}})', "{{compose_project}}")], w=6, thresholds=GREEN_RED)
    d.ts("Consumer lag by group / topic", [(f'sum by (consumergroup, topic) (kafka_consumergroup_lag{{{P}}})', "{{consumergroup}} / {{topic}}")], "short",
         desc="Messages produced but not yet committed by the group. Growing lag = consumers slower than producers; end-to-end latency grows with it.")
    d.ts("Produce rate (msg/s)", [(f'sum by (topic) (rate(kafka_topic_partition_current_offset{{{P}}}[$__rate_interval]))', "{{topic}}")], "ops")
    d.ts("Consume (commit) rate (msg/s)", [(f'sum by (consumergroup, topic) (rate(kafka_consumergroup_current_offset{{{P}}}[$__rate_interval]))', "{{consumergroup}} / {{topic}}")], "ops")
    d.ts("Lag by partition", [(f'kafka_consumergroup_lag{{{P}}}', "{{consumergroup}} {{topic}}[{{partition}}]")], "short",
         desc="Uneven lag across partitions points to key skew or one slow consumer.")

    tmpl = [var("compose_project", 'label_values({__name__=~"pg_up|redis_up|kafka_brokers"}, compose_project)', "Compose project")]
    return d.build("backend-lab-datastores", "backend-lab — Datastores", tmpl, LINKS)


# ------------------------------------------------------------------ traces
def traces():
    d = Dash()
    SV = 'service=~"$service"'
    d.text("How to read this dashboard",
           "Metrics here are generated by **Tempo metrics-generator** from spans and pushed to Prometheus "
           "(`traces_spanmetrics_*`, `traces_service_graph_*`). They need the stack in full mode and apps exporting OTLP to Alloy.\n\n"
           "Interactive service map: **Explore → Tempo → Service Graph** ([open](/explore?schemaVersion=1&panes=%7B%22a%22:%7B%22datasource%22:%22tempo%22,%22queries%22:%5B%7B%22refId%22:%22A%22,%22datasource%22:%7B%22type%22:%22tempo%22,%22uid%22:%22tempo%22%7D,%22queryType%22:%22serviceMap%22%7D%5D,%22range%22:%7B%22from%22:%22now-15m%22,%22to%22:%22now%22%7D%7D%7D)). "
           "Click an exemplar dot on a latency panel to jump to the trace.",
           h=5)
    d.row("Span RED metrics (span-metrics processor)")
    d.ts("Request rate by service / span", [(f'sum by (service, span_name) (rate(traces_spanmetrics_calls_total{{{SV}}}[$__rate_interval]))', "{{service}} · {{span_name}}")], "reqps")
    d.ts("Error ratio by service / span", [(f'sum by (service, span_name) (rate(traces_spanmetrics_calls_total{{{SV}, status_code="STATUS_CODE_ERROR"}}[$__rate_interval])) / sum by (service, span_name) (rate(traces_spanmetrics_calls_total{{{SV}}}[$__rate_interval]))', "{{service}} · {{span_name}}")],
         "percentunit", minv=0)
    for q, w in ((0.5, 8), (0.95, 8), (0.99, 8)):
        d.ts(f"Span latency p{int(q*100)}", [(f'histogram_quantile({q}, sum by (le, service, span_name) (rate(traces_spanmetrics_latency_bucket{{{SV}}}[$__rate_interval])))', "{{service}} · {{span_name}}")],
             "s", w=w)
    d.row("Service graph (service-graphs processor)")
    d.ts("Requests between services", [('sum by (client, server) (rate(traces_service_graph_request_total{client=~"$service|.*", server=~"$service"}[$__rate_interval]))', "{{client}} → {{server}}")], "reqps")
    d.ts("Failed requests between services", [('sum by (client, server) (rate(traces_service_graph_request_failed_total{server=~"$service"}[$__rate_interval]))', "{{client}} → {{server}}")], "reqps")
    d.ts("Edge latency p95 (server side)", [('histogram_quantile(0.95, sum by (le, client, server) (rate(traces_service_graph_request_server_seconds_bucket{server=~"$service"}[$__rate_interval])))', "{{client}} → {{server}}")], "s",
         desc="Latency measured by the server span of each edge. Compare with the client-side panel: the gap is network + queueing (e.g. time a message waited in Kafka).")
    d.ts("Edge latency p95 (client side)", [('histogram_quantile(0.95, sum by (le, client, server) (rate(traces_service_graph_request_client_seconds_bucket{server=~"$service"}[$__rate_interval])))', "{{client}} → {{server}}")], "s")
    tmpl = [var("service", "label_values(traces_spanmetrics_calls_total, service)", "Service")]
    return d.build("backend-lab-traces", "backend-lab — Service graph & spans (Tempo)", tmpl, LINKS)


# ------------------------------------------------------------------ JVM / HTTP / k6
def jvm():
    d = Dash()
    I = 'instance=~"$instance"'
    NA = 'uri!~"/actuator.*"'
    d.row("HTTP (Spring Boot / Micrometer)")
    d.ts("Request rate by status", [(f'sum by (status) (rate(http_server_requests_seconds_count{{{I}, {NA}}}[$__rate_interval]))', "{{status}}")], "reqps")
    d.ts("Error rate (5xx / total)", [(f'sum(rate(http_server_requests_seconds_count{{{I}, status=~"5..", {NA}}}[$__rate_interval])) / sum(rate(http_server_requests_seconds_count{{{I}, {NA}}}[$__rate_interval]))', "error ratio")], "percentunit")
    d.ts("Latency p50/p95/p99 (needs percentiles-histogram=true)",
         [(f'histogram_quantile({q}, sum by (le) (rate(http_server_requests_seconds_bucket{{{I}, {NA}}}[$__rate_interval])))', f"p{int(q*100)}") for q in (0.5, 0.95, 0.99)], "s",
         desc="Exemplars (dots) link to traces when tracing is enabled.")
    d.panels[-1]["targets"][0]["exemplar"] = True
    d.ts("Mean latency by uri", [(f'sum by (uri) (rate(http_server_requests_seconds_sum{{{I}, {NA}}}[$__rate_interval])) / sum by (uri) (rate(http_server_requests_seconds_count{{{I}, {NA}}}[$__rate_interval]))', "{{uri}}")], "s")

    d.row("JVM")
    d.ts("Heap used / committed / max", [(f'sum by (instance) (jvm_memory_used_bytes{{{I}, area="heap"}})', "used {{instance}}"),
                                        (f'sum by (instance) (jvm_memory_committed_bytes{{{I}, area="heap"}})', "committed {{instance}}"),
                                        (f'sum by (instance) (jvm_memory_max_bytes{{{I}, area="heap"}})', "max {{instance}}")], "bytes")
    d.ts("GC pause time / s", [(f'sum by (instance, gc) (rate(jvm_gc_pause_seconds_sum{{{I}}}[$__rate_interval]))', "{{gc}} {{instance}}")], "s")
    d.ts("CPU usage", [(f'process_cpu_usage{{{I}}}', "process {{instance}}"), (f'system_cpu_usage{{{I}}}', "system {{instance}}")], "percentunit")
    d.ts("Threads", [(f'jvm_threads_live_threads{{{I}}}', "live {{instance}}"), (f'jvm_threads_states_threads{{{I}, state="blocked"}}', "blocked {{instance}}")], "short")
    d.ts("Log events by level", [(f'sum by (level) (rate(logback_events_total{{{I}}}[$__rate_interval]))', "{{level}}")], "ops",
         desc="A burst of WARN/ERROR during a fault-injection scenario is expected; during a normal run it is a red flag.")

    d.row("Connection pool (HikariCP)")
    d.ts("HikariCP connections", [(f'hikaricp_connections_active{{{I}}}', "active {{pool}}"), (f'hikaricp_connections_idle{{{I}}}', "idle {{pool}}"),
                                  (f'hikaricp_connections_pending{{{I}}}', "pending {{pool}}"), (f'hikaricp_connections_max{{{I}}}', "max {{pool}}")], "short",
         desc="pending > 0 = threads waiting for a connection: the pool, not the database, is the bottleneck.")
    d.ts("HikariCP pool usage", [(f'hikaricp_connections_active{{{I}}} / hikaricp_connections_max{{{I}}}', "{{pool}}")], "percentunit", minv=0, maxv=1)
    d.ts("HikariCP acquire time (mean)", [(f'rate(hikaricp_connections_acquire_seconds_sum{{{I}}}[$__rate_interval]) / rate(hikaricp_connections_acquire_seconds_count{{{I}}}[$__rate_interval])', "{{pool}}")], "s")
    d.ts("HikariCP usage time (mean) & timeouts", [(f'rate(hikaricp_connections_usage_seconds_sum{{{I}}}[$__rate_interval]) / rate(hikaricp_connections_usage_seconds_count{{{I}}}[$__rate_interval])', "held {{pool}}"),
                                                    (f'rate(hikaricp_connections_timeout_total{{{I}}}[$__rate_interval])', "timeouts/s {{pool}}")], "s",
         desc="Usage = how long a connection is held per borrow (transaction length seen by the pool). Timeouts = SQLTransientConnectionException.")

    d.row("Kafka client (Spring Kafka / Micrometer)")
    d.ts("KafkaTemplate send rate", [(f'sum by (instance) (rate(spring_kafka_template_seconds_count{{{I}}}[$__rate_interval]))', "sends/s {{instance}}")], "ops",
         desc="Needs spring.kafka.template.observation-enabled=true.")
    d.ts("KafkaTemplate send latency (mean)", [(f'sum by (instance, result) (rate(spring_kafka_template_seconds_sum{{{I}}}[$__rate_interval])) / sum by (instance, result) (rate(spring_kafka_template_seconds_count{{{I}}}[$__rate_interval]))', "{{result}} {{instance}}")], "s")
    d.ts("Listener processing rate", [(f'sum by (instance, result) (rate(spring_kafka_listener_seconds_count{{{I}}}[$__rate_interval]))', "{{result}} {{instance}}")], "ops",
         desc="Needs spring.kafka.listener.observation-enabled=true.")
    d.ts("Listener processing time (mean)", [(f'sum by (instance) (rate(spring_kafka_listener_seconds_sum{{{I}}}[$__rate_interval])) / sum by (instance) (rate(spring_kafka_listener_seconds_count{{{I}}}[$__rate_interval]))', "{{instance}}")], "s")
    d.ts("Consumer max lag (client view)", [(f'max by (instance, client_id) (kafka_consumer_fetch_manager_records_lag_max{{{I}}})', "{{client_id}}")], "short",
         desc="Lag reported by the consumer client itself; compare with the broker-side lag on the Datastores dashboard.")

    d.row("k6 (remote write)")
    d.ts("k6 request rate", [('sum by (testid) (rate(k6_http_reqs_total[$__rate_interval]))', "reqs {{testid}}"),
                             ('sum by (testid) (rate(k6_http_reqs_total{expected_response="false"}[$__rate_interval]))', "failed {{testid}}")], "reqps")
    d.ts("k6 http_req_duration p50/p95/p99", [('max by (testid) (k6_http_req_duration_p50)', "p50 {{testid}}"),
                                              ('max by (testid) (k6_http_req_duration_p95)', "p95 {{testid}}"),
                                              ('max by (testid) (k6_http_req_duration_p99)', "p99 {{testid}}")], "s")
    d.ts("k6 VUs", [('sum(k6_vus)', "vus"), ('sum(k6_vus_max)', "vus max")], "short")
    d.ts("k6 dropped iterations", [('sum(rate(k6_dropped_iterations_total[$__rate_interval]))', "dropped/s")], "short",
         desc="Dropped iterations with an arrival-rate executor = the generator could not keep the target rate (not enough VUs, or the load generator itself is saturated).")

    tmpl = [{"name": "instance", "label": "Instance", "type": "query", "datasource": DS,
             "query": {"query": "label_values(jvm_info, instance)", "refId": "instance"}, "definition": "label_values(jvm_info, instance)",
             "includeAll": True, "multi": True, "allValue": ".*", "current": {"selected": True, "text": ["All"], "value": ["$__all"]}, "refresh": 2}]
    return d.build("backend-lab-jvm-http", "backend-lab — JVM / HTTP / k6", tmpl, LINKS)


for name, fn in (("containers.json", containers), ("datastores.json", datastores), ("traces.json", traces), ("jvm-http.json", jvm)):
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as f:
        json.dump(fn(), f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("wrote", name)
