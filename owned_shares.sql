CREATE TABLE IF NOT EXISTS owned_shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	user_id INTEGER NOT NULL,
	company TEXT NOT NULL,
	symbol TEXT NOT NULL,
	total_shares NUMERIC DEFAULT 0,
	date CURRENT_TIMESTAMP
);

