-- =====================================================================
-- LifeOS AI — Schéma PostgreSQL de production
-- Le prototype backend (Phase 1) utilise SQLite avec un sous-ensemble
-- de ces tables (users, tasks, habits, goals, memories, chat_messages).
-- Ce fichier décrit le modèle de données cible complet.
-- Nécessite l'extension pgvector pour les embeddings de la mémoire IA.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ---------------------------------------------------------------------
-- Utilisateurs & sécurité
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255),
    timezone        VARCHAR(64) DEFAULT 'Europe/Paris',
    created_at      TIMESTAMPTZ DEFAULT now(),
    deleted_at      TIMESTAMPTZ  -- soft delete pour conformité RGPD
);

CREATE TABLE oauth_connections (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       UUID REFERENCES users(id) ON DELETE CASCADE,
    provider      VARCHAR(50) NOT NULL,  -- google_calendar | apple_health | strava | garmin | fitbit ...
    access_token  TEXT NOT NULL,          -- chiffré au niveau applicatif
    refresh_token TEXT,
    scope         TEXT,
    expires_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Tâches & objectifs
-- ---------------------------------------------------------------------
CREATE TABLE tasks (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    title        VARCHAR(255) NOT NULL,
    description  TEXT,
    due_date     TIMESTAMPTZ,
    priority     VARCHAR(20) DEFAULT 'medium',
    status       VARCHAR(20) DEFAULT 'todo',
    created_at   TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE goals (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    title        VARCHAR(255) NOT NULL,
    category     VARCHAR(50),  -- carriere | sport | finance | apprentissage | relations
    target_date  DATE,
    progress     FLOAT DEFAULT 0.0,
    status       VARCHAR(20) DEFAULT 'active',
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE goal_milestones (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id     UUID REFERENCES goals(id) ON DELETE CASCADE,
    title       VARCHAR(255) NOT NULL,
    target_date DATE,
    done        BOOLEAN DEFAULT FALSE
);

-- ---------------------------------------------------------------------
-- Habitudes
-- ---------------------------------------------------------------------
CREATE TABLE habits (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID REFERENCES users(id) ON DELETE CASCADE,
    name             VARCHAR(255) NOT NULL,
    category         VARCHAR(50),
    target_frequency INT DEFAULT 7,
    created_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE habit_logs (
    id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    habit_id  UUID REFERENCES habits(id) ON DELETE CASCADE,
    date      DATE DEFAULT CURRENT_DATE,
    completed BOOLEAN DEFAULT TRUE,
    note      TEXT
);

-- ---------------------------------------------------------------------
-- Mémoire IA (RAG) & conversations
-- ---------------------------------------------------------------------
CREATE TABLE memories (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    content    TEXT NOT NULL,
    category   VARCHAR(50),  -- preference | objectif | habitude | contexte
    embedding  vector(1536),  -- dimension selon le modèle d'embeddings utilisé
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX memories_embedding_idx ON memories USING ivfflat (embedding vector_cosine_ops);

CREATE TABLE chat_messages (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    role       VARCHAR(20) NOT NULL,  -- user | assistant
    content    TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Calendrier & notifications
-- ---------------------------------------------------------------------
CREATE TABLE calendar_events (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID REFERENCES users(id) ON DELETE CASCADE,
    external_provider VARCHAR(50),   -- google | apple | outlook | null (natif)
    external_id      VARCHAR(255),
    title            VARCHAR(255) NOT NULL,
    start_at         TIMESTAMPTZ NOT NULL,
    end_at           TIMESTAMPTZ NOT NULL,
    location         VARCHAR(255),
    created_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE notifications (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    type       VARCHAR(50),  -- tache | habitude | motivation | sante | objectif | suggestion
    title      VARCHAR(255) NOT NULL,
    body       TEXT,
    scheduled_at TIMESTAMPTZ,
    sent_at    TIMESTAMPTZ,
    read_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Sport & santé
-- ---------------------------------------------------------------------
CREATE TABLE workouts (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    type        VARCHAR(50),  -- course | musculation | yoga | cyclisme ...
    duration_min INT,
    calories    INT,
    performed_at TIMESTAMPTZ,
    source       VARCHAR(50),  -- manuel | apple_health | strava | garmin
    raw_data     JSONB,
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE body_metrics (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    weight_kg  FLOAT,
    body_fat_pct FLOAT,
    measured_at TIMESTAMPTZ DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Nutrition
-- ---------------------------------------------------------------------
CREATE TABLE nutrition_logs (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    description TEXT,
    photo_url  VARCHAR(500),
    calories   INT,
    protein_g  FLOAT,
    carbs_g    FLOAT,
    fat_g      FLOAT,
    logged_at  TIMESTAMPTZ DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Finances personnelles
-- ---------------------------------------------------------------------
CREATE TABLE financial_transactions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    amount      NUMERIC(12,2) NOT NULL,
    currency    VARCHAR(3) DEFAULT 'EUR',
    category    VARCHAR(50),
    description VARCHAR(255),
    occurred_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE budgets (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    category     VARCHAR(50) NOT NULL,
    monthly_limit NUMERIC(12,2) NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Journal personnel
-- ---------------------------------------------------------------------
CREATE TABLE journal_entries (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    content    TEXT NOT NULL,
    mood_score INT,  -- 1-10
    ai_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Index utiles
-- ---------------------------------------------------------------------
CREATE INDEX idx_tasks_user ON tasks(user_id, status);
CREATE INDEX idx_habits_user ON habits(user_id);
CREATE INDEX idx_habit_logs_habit_date ON habit_logs(habit_id, date);
CREATE INDEX idx_goals_user ON goals(user_id, status);
CREATE INDEX idx_notifications_user_sched ON notifications(user_id, scheduled_at);
CREATE INDEX idx_calendar_user_start ON calendar_events(user_id, start_at);
CREATE INDEX idx_financial_user_date ON financial_transactions(user_id, occurred_at);
