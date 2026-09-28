CREATE TABLE archivals (
	id TEXT PRIMARY KEY,
	created_at TEXT NOT NULL,
	placement_id TEXT NOT NULL REFERENCES placements (id) ON DELETE CASCADE,
	user_id TEXT NOT NULL REFERENCES users (id),
	UNIQUE (placement_id, user_id)
) STRICT;

CREATE INDEX archivals_user_id ON archivals (user_id);
