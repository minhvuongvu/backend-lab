-- Example schema: REPLACE with the topic schema (02-system-design.html §7).
-- Shared by before and every implementation; implementation-specific tables go in later migrations
-- and are documented per column/index in 03-implementation.html.
CREATE TABLE item (
    id          UUID PRIMARY KEY,                -- caller-generated: lets k6 and the integrity checker track each request
    payload     TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL
);
