CREATE TABLE villas (
    id text PRIMARY KEY,
    capacity integer NOT NULL CHECK (capacity > 0),
    data jsonb NOT NULL
);
CREATE TABLE inventory_days (
    villa_id text NOT NULL REFERENCES villas(id),
    night date NOT NULL,
    open boolean NOT NULL,
    PRIMARY KEY (villa_id, night)
);
CREATE TABLE bookings (
    id bigserial PRIMARY KEY,
    villa_id text NOT NULL REFERENCES villas(id),
    check_in date NOT NULL,
    check_out date NOT NULL CHECK (check_out > check_in),
    status text NOT NULL CHECK (status IN ('confirmed', 'cancelled'))
);
ALTER TABLE turns ADD COLUMN availability jsonb;
