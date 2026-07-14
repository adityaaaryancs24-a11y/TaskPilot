CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    source_type VARCHAR(50) NOT NULL,
    priority VARCHAR(10),
    severity VARCHAR(10),
    deadline TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    merged_from JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    confidence_score FLOAT,
    grounding_evidence JSONB,
    embedding VECTOR(384)
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_source ON tasks(source_type);
CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);

CREATE TABLE IF NOT EXISTS runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    plan JSONB NOT NULL,
    ranked_task_ids UUID[],
    execution_time_ms INTEGER,
    triggered_by VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON runs(run_timestamp);

CREATE TABLE IF NOT EXISTS task_run_mapping (
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    rank INTEGER,
    score FLOAT,
    PRIMARY KEY (task_id, run_id)
);

CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    feedback_type VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id);

CREATE TABLE IF NOT EXISTS preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    preference_key VARCHAR(255) NOT NULL,
    preference_value FLOAT NOT NULL,
    version INTEGER DEFAULT 1,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (user_id, preference_key, version)
);

CREATE INDEX IF NOT EXISTS idx_preferences_user ON preferences(user_id);

CREATE TABLE IF NOT EXISTS preference_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    preference_key VARCHAR(255) NOT NULL,
    old_value FLOAT,
    new_value FLOAT,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    changed_by VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS chat_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255),
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    tokens_used INTEGER,
    response_time_ms INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_log(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_timestamp ON chat_log(timestamp);

CREATE TABLE IF NOT EXISTS traces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    input JSONB,
    output JSONB,
    execution_time_ms INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_traces_run ON traces(run_id);
CREATE INDEX IF NOT EXISTS idx_traces_agent ON traces(agent_name);

CREATE TABLE IF NOT EXISTS llm_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_hash VARCHAR(64) UNIQUE NOT NULL,
    prompt TEXT NOT NULL,
    response JSONB NOT NULL,
    model_used VARCHAR(100),
    tokens_used INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_cache_prompt_hash ON llm_cache(prompt_hash);
CREATE INDEX IF NOT EXISTS idx_cache_expiry ON llm_cache(expires_at);

CREATE TABLE IF NOT EXISTS websocket_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    connection_id VARCHAR(255) UNIQUE NOT NULL,
    connected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    disconnected_at TIMESTAMP WITH TIME ZONE,
    last_ping TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ws_user ON websocket_connections(user_id);

CREATE OR REPLACE VIEW active_tasks AS
SELECT * FROM tasks WHERE status IN ('open', 'in-progress');

CREATE OR REPLACE VIEW user_insights AS
SELECT
    user_id,
    COUNT(feedback.id) as total_feedback,
    AVG(rating) as avg_rating,
    COUNT(DISTINCT task_id) as tasks_touched
FROM feedback
GROUP BY user_id;
