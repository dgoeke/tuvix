CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, actor TEXT);

-- CREATE TRIGGER delete_tail AFTER INSERT ON messages
--   BEGIN
--     DELETE FROM messages WHERE id < NEW.id-10;
--   END;
