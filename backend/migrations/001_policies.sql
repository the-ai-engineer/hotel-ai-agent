CREATE TABLE documents (
    id text NOT NULL,
    revision integer NOT NULL CHECK (revision > 0),
    title text NOT NULL,
    summary text NOT NULL,
    keywords jsonb NOT NULL,
    body text NOT NULL,
    published boolean NOT NULL,
    PRIMARY KEY (id, revision)
);
CREATE TABLE guest_sessions (
    token_hash text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL DEFAULT now() + interval '24 hours',
    active_turn uuid,
    busy_until timestamptz
);
CREATE TABLE turns (
    id uuid PRIMARY KEY,
    session_hash text NOT NULL REFERENCES guest_sessions(token_hash) ON DELETE CASCADE,
    question text NOT NULL,
    answer text,
    sources jsonb,
    status text NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'interrupted')),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX turns_session_time ON turns(session_hash, created_at);
