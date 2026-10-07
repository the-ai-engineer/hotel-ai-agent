ALTER TABLE turns ADD COLUMN deadline_at timestamptz;
UPDATE turns t SET deadline_at=COALESCE(s.busy_until,t.created_at+interval '90 seconds')
FROM guest_sessions s WHERE s.token_hash=t.session_hash;
ALTER TABLE turns ALTER COLUMN deadline_at SET NOT NULL;
ALTER TABLE turns ALTER COLUMN deadline_at SET DEFAULT now()+interval '90 seconds';
CREATE TABLE rate_counters (
    scope text NOT NULL,
    bucket timestamptz NOT NULL,
    used integer NOT NULL CHECK (used>0),
    expires_at timestamptz NOT NULL,
    PRIMARY KEY (scope,bucket)
);
CREATE INDEX rate_counters_expiry ON rate_counters(expires_at);
