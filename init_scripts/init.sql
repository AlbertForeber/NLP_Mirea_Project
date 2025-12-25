CREATE TABLE IF NOT EXISTS  users(
    telegram_id INT PRIMARY KEY,
    user_name VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS categories(
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(50) UNIQUE
);

CREATE TABLE IF NOT EXISTS notes(
    note_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    note_name VARCHAR(50),

    FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS note_category(
    compound_id SERIAL PRIMARY KEY,
    note_id INT NOT NULL REFERENCES notes(note_id) ON DELETE CASCADE,
    category_id INT NOT NULL REFERENCES categories(category_id) ON DELETE CASCADE,
    thought_count INT NOT NULL,

    UNIQUE (note_id, category_id)
);

CREATE OR REPLACE FUNCTION check_if_there_thoughts()
RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.thought_count = 0 THEN
            DELETE FROM note_category WHERE compound_id = NEW.compound_id;
            RETURN NULL;
        END IF;
        RETURN NEW;
    END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_thought_amount
AFTER UPDATE ON note_category
FOR EACH ROW
EXECUTE FUNCTION check_if_there_thoughts();

