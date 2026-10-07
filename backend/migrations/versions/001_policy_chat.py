from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    statements = [
        "CREATE TABLE schema_contract(id integer PRIMARY KEY CHECK(id=1),schema_version integer NOT NULL,min_app_schema integer NOT NULL)",
        "INSERT INTO schema_contract VALUES(1,1,1)",
        "CREATE TABLE guest_sessions(id uuid PRIMARY KEY,token_hash text UNIQUE NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),expires_at timestamptz NOT NULL DEFAULT clock_timestamp()+interval '24 hours')",
        "CREATE TABLE conversations(id uuid PRIMARY KEY,owner_id uuid NOT NULL REFERENCES guest_sessions ON DELETE CASCADE,created_at timestamptz NOT NULL DEFAULT clock_timestamp())",
        "CREATE TABLE turns(conversation_id uuid NOT NULL REFERENCES conversations ON DELETE CASCADE,client_turn_id uuid NOT NULL,message text NOT NULL CHECK(length(message) BETWEEN 1 AND 2000),state text NOT NULL DEFAULT 'running' CHECK(state IN ('running','completed','failed','interrupted')),created_at timestamptz NOT NULL DEFAULT clock_timestamp(),deadline timestamptz NOT NULL,result jsonb,error_code text,PRIMARY KEY(conversation_id,client_turn_id))",
        "CREATE UNIQUE INDEX one_running_turn ON turns(conversation_id) WHERE state='running'",
        "CREATE INDEX turn_history ON turns(conversation_id,created_at,client_turn_id)",
        "CREATE TABLE policy_versions(id uuid PRIMARY KEY,slug text NOT NULL,title text NOT NULL,version integer NOT NULL CHECK(version>0),published boolean NOT NULL DEFAULT false,superseded boolean NOT NULL DEFAULT false,UNIQUE(slug,version))",
        "CREATE UNIQUE INDEX one_current_policy ON policy_versions(slug) WHERE published AND NOT superseded",
        "CREATE TABLE policy_sections(id uuid PRIMARY KEY,version_id uuid NOT NULL REFERENCES policy_versions ON DELETE CASCADE,position integer NOT NULL,body text NOT NULL,search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english',body)) STORED)",
        "CREATE INDEX policy_search ON policy_sections USING gin(search_vector)",
    ]
    for statement in statements:
        op.execute(statement)


def downgrade():
    for table in [
        "policy_sections",
        "policy_versions",
        "turns",
        "conversations",
        "guest_sessions",
        "schema_contract",
    ]:
        op.execute(f"DROP TABLE {table}")
