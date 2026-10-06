ALTER TABLE guest_sessions ADD COLUMN conversation_id uuid NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE turns ADD COLUMN conversation_id uuid;
UPDATE turns t SET conversation_id=s.conversation_id FROM guest_sessions s WHERE t.session_hash=s.token_hash;
ALTER TABLE turns ALTER COLUMN conversation_id SET NOT NULL;
CREATE INDEX turns_conversation_time ON turns(conversation_id,created_at);
