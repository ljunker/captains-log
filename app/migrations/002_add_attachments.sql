CREATE TABLE attachments (
    id INTEGER NOT NULL,
    entry_id INTEGER NOT NULL,
    kind VARCHAR(16) NOT NULL,
    storage_key VARCHAR(255) NOT NULL,
    thumbnail_key VARCHAR(255),
    original_filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size INTEGER NOT NULL,
    sort_order INTEGER DEFAULT 0 NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(entry_id) REFERENCES entries (id)
);

CREATE INDEX ix_attachments_entry_id ON attachments (entry_id);
CREATE UNIQUE INDEX ix_attachments_storage_key ON attachments (storage_key);
