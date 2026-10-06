from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE TABLE rate_buckets(scope text NOT NULL,key_hash text NOT NULL,window_start bigint NOT NULL,admitted integer NOT NULL CHECK(admitted>0),expires_at timestamptz NOT NULL,PRIMARY KEY(scope,key_hash,window_start))"
    )
    op.execute("CREATE INDEX expired_buckets ON rate_buckets(expires_at)")
    op.execute("UPDATE schema_contract SET schema_version=3 WHERE id=1")


def downgrade():
    op.execute("DROP TABLE rate_buckets")
    op.execute("UPDATE schema_contract SET schema_version=2 WHERE id=1")
