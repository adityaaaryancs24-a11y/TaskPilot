CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    tasks_json TEXT NOT NULL,
    plan_json TEXT,
    pipeline_status TEXT NOT NULL DEFAULT 'ok'
);

CREATE TABLE IF NOT EXISTS chat_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    referenced_task_ids TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    step_name TEXT NOT NULL,
    duration_ms REAL,
    tokens_used INTEGER DEFAULT 0,
    status TEXT DEFAULT 'ok'
);

CREATE TABLE IF NOT EXISTS llm_extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    tasks_extracted INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    latency_ms REAL DEFAULT 0,
    status TEXT DEFAULT 'ok'
);

CREATE TABLE IF NOT EXISTS weekly_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start TEXT NOT NULL,
    summary_json TEXT,
    generated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL UNIQUE,
    last_sync TEXT,
    status TEXT DEFAULT 'idle',
    error TEXT,
    items_fetched INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source_type TEXT,
    payload TEXT,
    processed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS agent_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ok',
    duration_ms REAL,
    details TEXT
);

CREATE TABLE IF NOT EXISTS user_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    action TEXT,
    user_preference TEXT,
    timestamp TEXT
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT DEFAULT 'info',
    title TEXT,
    message TEXT,
    task_id TEXT,
    dismissed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS dedup_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    match_confidence REAL DEFAULT 0.0,
    reasoning TEXT DEFAULT '',
    matched_on TEXT DEFAULT 'title',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    preference_key TEXT NOT NULL UNIQUE,
    preference_value TEXT NOT NULL DEFAULT '',
    source TEXT DEFAULT 'inferred',
    confidence REAL DEFAULT 0.5,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS completion_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    task_title TEXT NOT NULL,
    task_source_type TEXT,
    completed_at TEXT NOT NULL,
    completion_hour INTEGER,
    day_of_week INTEGER,
    time_to_complete_hours REAL,
    task_priority TEXT
);

CREATE TABLE IF NOT EXISTS calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    is_all_day INTEGER DEFAULT 0,
    source TEXT DEFAULT 'simulated'
);

CREATE TABLE IF NOT EXISTS agent_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    memory_key TEXT NOT NULL,
    memory_value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS oauth_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'demo-user',
    provider TEXT NOT NULL,
    access_token TEXT NOT NULL,
    scope TEXT,
    github_login TEXT,
    connected_at TEXT NOT NULL,
    UNIQUE(user_id, provider)
);
