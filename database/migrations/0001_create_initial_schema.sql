CREATE TABLE users (
	id TEXT PRIMARY KEY,
	created_at TEXT NOT NULL,
	name TEXT NOT NULL COLLATE NOCASE UNIQUE,
	open_in_new_tab INTEGER NOT NULL CHECK (open_in_new_tab IN (0, 1))
) STRICT;

CREATE TABLE recoveries (
	id TEXT PRIMARY KEY,
	created_at TEXT NOT NULL,
	user_id TEXT NOT NULL REFERENCES users (id),
	code TEXT NOT NULL
) STRICT;

CREATE INDEX recoveries_user_id ON recoveries (user_id);

CREATE TABLE invites (
	id TEXT PRIMARY KEY,
	created_at TEXT NOT NULL,
	token TEXT NOT NULL UNIQUE,
	creator_id TEXT NOT NULL REFERENCES users (id),
	target_id TEXT REFERENCES users (id),
	expires_at TEXT NOT NULL
) STRICT;

CREATE INDEX invites_creator_id ON invites (creator_id);
CREATE INDEX invites_target_id ON invites (target_id);

CREATE TABLE pins (
	id TEXT PRIMARY KEY,
	created_at TEXT NOT NULL,
	url TEXT NOT NULL,
	title TEXT NOT NULL,
	note TEXT NOT NULL,
	creator_id TEXT NOT NULL REFERENCES users (id)
) STRICT;

CREATE INDEX pins_creator_id ON pins (creator_id);

CREATE TABLE boards (
	id TEXT PRIMARY KEY,
	created_at TEXT NOT NULL,
	title TEXT NOT NULL,
	creator_id TEXT NOT NULL REFERENCES users (id)
) STRICT;

CREATE INDEX boards_creator_id ON boards (creator_id);

-- Positions are not unique: reordering swaps them row by row, so duplicates
-- exist briefly within a request.
CREATE TABLE placements (
	id TEXT PRIMARY KEY,
	created_at TEXT NOT NULL,
	pin_id TEXT NOT NULL REFERENCES pins (id) ON DELETE CASCADE,
	board_id TEXT NOT NULL REFERENCES boards (id) ON DELETE CASCADE,
	adder_id TEXT NOT NULL REFERENCES users (id),
	position INTEGER NOT NULL,
	UNIQUE (pin_id, board_id)
) STRICT;

CREATE INDEX placements_board_id ON placements (board_id);

CREATE TABLE shares (
	id TEXT PRIMARY KEY,
	created_at TEXT NOT NULL,
	board_id TEXT NOT NULL REFERENCES boards (id) ON DELETE CASCADE,
	user_id TEXT NOT NULL REFERENCES users (id),
	UNIQUE (board_id, user_id)
) STRICT;

CREATE INDEX shares_user_id ON shares (user_id);

CREATE TABLE orderings (
	id TEXT PRIMARY KEY,
	created_at TEXT NOT NULL,
	user_id TEXT NOT NULL REFERENCES users (id),
	board_id TEXT NOT NULL REFERENCES boards (id) ON DELETE CASCADE,
	position INTEGER NOT NULL,
	UNIQUE (user_id, board_id)
) STRICT;

CREATE INDEX orderings_board_id ON orderings (board_id);
