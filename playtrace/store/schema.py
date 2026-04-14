SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS titles (
    title_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    classification TEXT NOT NULL,
    classification_confidence TEXT NOT NULL,
    title_confidence TEXT NOT NULL,
    launcher TEXT,
    confirmed_seconds INTEGER NOT NULL DEFAULT 0,
    estimated_seconds INTEGER NOT NULL DEFAULT 0,
    foreground_seconds INTEGER NOT NULL DEFAULT 0,
    runtime_confidence TEXT NOT NULL,
    launches_confirmed INTEGER NOT NULL DEFAULT 0,
    launches_inferred INTEGER NOT NULL DEFAULT 0,
    launches_gui INTEGER NOT NULL DEFAULT 0,
    launches_confidence TEXT NOT NULL,
    first_seen TEXT,
    last_seen TEXT,
    evidence_sources TEXT NOT NULL,
    tags TEXT NOT NULL,
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    title_id TEXT,
    exe_id TEXT NOT NULL,
    user_sid TEXT,
    started_at TEXT,
    ended_at TEXT,
    duration_seconds INTEGER,
    foreground_seconds INTEGER NOT NULL DEFAULT 0,
    bytes_in INTEGER NOT NULL DEFAULT 0,
    bytes_out INTEGER NOT NULL DEFAULT 0,
    confidence TEXT NOT NULL,
    evidence_sources TEXT NOT NULL,
    parent_chain TEXT NOT NULL,
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS executables (
    exe_id TEXT PRIMARY KEY,
    normalized_key TEXT NOT NULL,
    path TEXT,
    filename TEXT,
    original_filename TEXT,
    product_name TEXT,
    file_description TEXT,
    signer TEXT,
    company_name TEXT,
    sha1 TEXT,
    classification TEXT NOT NULL,
    classification_confidence TEXT NOT NULL,
    ignored INTEGER NOT NULL DEFAULT 0,
    first_seen TEXT,
    last_seen TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    title_id TEXT,
    exe_id TEXT NOT NULL,
    user_sid TEXT,
    started_at TEXT,
    ended_at TEXT,
    duration_seconds INTEGER,
    foreground_seconds INTEGER NOT NULL DEFAULT 0,
    bytes_in INTEGER NOT NULL DEFAULT 0,
    bytes_out INTEGER NOT NULL DEFAULT 0,
    confidence TEXT NOT NULL,
    evidence_sources TEXT NOT NULL,
    parent_chain TEXT NOT NULL,
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS titles (
    title_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    classification TEXT NOT NULL,
    classification_confidence TEXT NOT NULL,
    title_confidence TEXT NOT NULL,
    launcher TEXT,
    confirmed_seconds INTEGER NOT NULL DEFAULT 0,
    estimated_seconds INTEGER NOT NULL DEFAULT 0,
    foreground_seconds INTEGER NOT NULL DEFAULT 0,
    runtime_confidence TEXT NOT NULL,
    launches_confirmed INTEGER NOT NULL DEFAULT 0,
    launches_inferred INTEGER NOT NULL DEFAULT 0,
    launches_gui INTEGER NOT NULL DEFAULT 0,
    launches_confidence TEXT NOT NULL,
    first_seen TEXT,
    last_seen TEXT,
    evidence_sources TEXT NOT NULL,
    tags TEXT NOT NULL,
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mappings (
    mapping_id TEXT PRIMARY KEY,
    target TEXT NOT NULL,
    title TEXT NOT NULL,
    classification TEXT,
    launcher TEXT,
    ignore INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    confidence TEXT NOT NULL
);
"""