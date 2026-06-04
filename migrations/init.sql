-- ============================================================
--  Multiagent Sales Assistant — initial schema
-- ============================================================

CREATE TABLE IF NOT EXISTS clients (
    id             SERIAL PRIMARY KEY,
    name           VARCHAR(255) NOT NULL,
    contact_info   JSONB        NOT NULL DEFAULT '{}',
    source_channel VARCHAR(100),
    created_at     TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS managers (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    email      VARCHAR(255) UNIQUE NOT NULL,
    role       VARCHAR(50)  NOT NULL DEFAULT 'manager',
    created_at TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_base (
    id         SERIAL PRIMARY KEY,
    category   VARCHAR(100) NOT NULL,
    content    TEXT         NOT NULL,
    updated_at TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS appeals (
    id                 SERIAL PRIMARY KEY,
    client_id          INTEGER      NOT NULL REFERENCES clients(id),
    text               TEXT         NOT NULL,
    status             VARCHAR(50)  NOT NULL DEFAULT 'new',
    created_at         TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at         TIMESTAMP    NOT NULL DEFAULT now(),
    assigned_manager_id INTEGER     REFERENCES managers(id),
    source_channel     VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS recommendations (
    id          SERIAL PRIMARY KEY,
    appeal_id   INTEGER   NOT NULL REFERENCES appeals(id),
    manager_id  INTEGER   NOT NULL REFERENCES managers(id),
    content     TEXT      NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT now(),
    is_applied  BOOLEAN   NOT NULL DEFAULT FALSE,
    applied_at  TIMESTAMP
);

CREATE TABLE IF NOT EXISTS commercial_offers (
    id          SERIAL PRIMARY KEY,
    appeal_id   INTEGER        NOT NULL REFERENCES appeals(id),
    content     JSONB          NOT NULL DEFAULT '{}',
    total_price NUMERIC(12,2)  NOT NULL DEFAULT 0,
    status      VARCHAR(50)    NOT NULL DEFAULT 'draft',
    created_at  TIMESTAMP      NOT NULL DEFAULT now(),
    sent_at     TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deals (
    id               SERIAL PRIMARY KEY,
    appeal_id        INTEGER       NOT NULL REFERENCES appeals(id),
    probability      NUMERIC(5,2)  NOT NULL DEFAULT 0,
    status           VARCHAR(50)   NOT NULL DEFAULT 'open',
    expected_close_at DATE,
    actual_close_at  DATE,
    created_at       TIMESTAMP     NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recommendations_knowledge (
    id                INTEGER   NOT NULL REFERENCES recommendations(id),
    recommendation_id INTEGER   NOT NULL REFERENCES recommendations(id),
    knowledge_id      INTEGER   NOT NULL REFERENCES knowledge_base(id),
    created_at        TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (recommendation_id, knowledge_id)
);

CREATE TABLE IF NOT EXISTS analytics (
    id               SERIAL PRIMARY KEY,
    manager_id       INTEGER       NOT NULL REFERENCES managers(id),
    period_start     DATE          NOT NULL,
    period_end       DATE          NOT NULL,
    leads_count      INTEGER       NOT NULL DEFAULT 0,
    converted_deals  INTEGER       NOT NULL DEFAULT 0,
    conversion_rate  NUMERIC(5,2)  NOT NULL DEFAULT 0,
    revenue          NUMERIC(14,2) NOT NULL DEFAULT 0,
    created_at       TIMESTAMP     NOT NULL DEFAULT now()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_appeals_client_id     ON appeals(client_id);
CREATE INDEX IF NOT EXISTS idx_appeals_status        ON appeals(status);
CREATE INDEX IF NOT EXISTS idx_deals_appeal_id       ON deals(appeal_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_appeal ON recommendations(appeal_id);
