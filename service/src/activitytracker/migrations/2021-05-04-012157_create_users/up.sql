CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL,
    password_hash VARCHAR NOT NULL,
    admin BOOLEAN NOT NULL DEFAULT 't'
)