CREATE TABLE tags (
    id INTEGER NOT NULL,
    name VARCHAR(40) NOT NULL,
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_tags_name ON tags (name);

CREATE TABLE entry_tags (
    entry_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (entry_id, tag_id),
    FOREIGN KEY(entry_id) REFERENCES entries (id),
    FOREIGN KEY(tag_id) REFERENCES tags (id)
);

CREATE INDEX ix_entry_tags_tag_id ON entry_tags (tag_id);
