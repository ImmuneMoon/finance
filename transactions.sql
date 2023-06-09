CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	user_id INTEGER NOT NULL,
	user_transaction NUMERIC DEFAULT 0,
	company TEXT NOT NULL,
	symbol TEXT NOT NULL,
	shares NUMERIC NOT NULL DEFAULT 0,
	total_shares NUMERIC DEFAULT 0,
	price NUMERIC NOT NULL,
	transaction_type TEXT NOT NULL,
	date CURRENT_TIMESTAMP NOT NULL
);

