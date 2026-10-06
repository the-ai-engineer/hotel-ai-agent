ALTER TABLE bookings ADD COLUMN reference text UNIQUE;
ALTER TABLE bookings ADD COLUMN request_id uuid UNIQUE;
ALTER TABLE bookings ADD COLUMN session_hash text REFERENCES guest_sessions(token_hash) ON DELETE CASCADE;
ALTER TABLE bookings ADD COLUMN guests integer CHECK (guests BETWEEN 1 AND 8);
ALTER TABLE bookings ADD COLUMN created_at timestamptz NOT NULL DEFAULT now();
CREATE INDEX bookings_owner ON bookings(session_hash, created_at);
CREATE TABLE hotel_requests (
    id uuid PRIMARY KEY,
    booking_id bigint NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    conversation_id uuid NOT NULL,
    note text NOT NULL CHECK (length(note) BETWEEN 1 AND 1000),
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'pending_review', 'superseded')),
    expires_at timestamptz NOT NULL DEFAULT now() + interval '10 minutes',
    created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE turns ADD COLUMN request_id uuid REFERENCES hotel_requests(id) ON DELETE SET NULL;
