CREATE TABLE polls_poll (
    id SERIAL PRIMARY KEY,
    question VARCHAR(255) NOT NULL UNIQUE,
    text JSONB NOT NULL
);


-- Load data into polls_poll table
COPY polls_poll (id, question, text)
FROM '/data/polls.csv'
DELIMITER ','
CSV HEADER;


-- Reset the ID sequence correctly
SELECT setval('polls_poll_id_seq', (SELECT MAX(id) FROM polls_poll));