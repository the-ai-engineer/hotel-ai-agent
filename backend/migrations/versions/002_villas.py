from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    for sql in [
        "CREATE TABLE villas(id uuid PRIMARY KEY,slug text UNIQUE NOT NULL,name text NOT NULL,description text NOT NULL,capacity integer NOT NULL CHECK(capacity BETWEEN 1 AND 8),amenities jsonb NOT NULL,image text NOT NULL,active boolean NOT NULL DEFAULT true)",
        "CREATE TABLE inventory_days(villa_id uuid NOT NULL REFERENCES villas ON DELETE CASCADE,day date NOT NULL,open boolean NOT NULL DEFAULT true,PRIMARY KEY(villa_id,day))",
        "CREATE TABLE bookings(id uuid PRIMARY KEY,villa_id uuid NOT NULL REFERENCES villas ON DELETE CASCADE,check_in date NOT NULL,check_out date NOT NULL,status text NOT NULL CHECK(status IN ('blocking','cancelled')),CHECK(check_out>check_in))",
        "CREATE INDEX booking_overlap ON bookings(villa_id,check_in,check_out) WHERE status='blocking'",
        "CREATE TABLE demo_inventory(id integer PRIMARY KEY CHECK(id=1),starts_on date NOT NULL,ends_on date NOT NULL,CHECK(ends_on>starts_on))",
        "UPDATE schema_contract SET schema_version=2 WHERE id=1",
    ]:
        op.execute(sql)


def downgrade():
    for table in ["bookings", "inventory_days", "villas", "demo_inventory"]:
        op.execute(f"DROP TABLE {table}")
    op.execute("UPDATE schema_contract SET schema_version=1 WHERE id=1")
