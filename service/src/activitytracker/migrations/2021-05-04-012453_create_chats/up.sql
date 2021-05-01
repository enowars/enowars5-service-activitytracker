CREATE TABLE chats (
    id SERIAL PRIMARY KEY,
    user_1 INT NOT NULL REFERENCES users(id),
    user_2 INT NOT NULL REFERENCES users(id),
    name VARCHAR NOT NULL
)