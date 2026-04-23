-- Session-scoped metadata sidecar (per Copilot thread_id). Run once per MySQL database.
-- The WLR agent can CREATE/INSERT/UPDATE via the execute_metadata_sql tool.

CREATE TABLE IF NOT EXISTS session_metadata (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  thread_id CHAR(36) NOT NULL,
  source_label VARCHAR(512) NULL,
  entity_key VARCHAR(512) NOT NULL,
  attr_key VARCHAR(512) NOT NULL,
  attr_value TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_session_metadata_thread (thread_id),
  KEY idx_session_metadata_thread_entity (thread_id, entity_key(128))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
