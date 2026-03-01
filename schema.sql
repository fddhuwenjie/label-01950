CREATE TABLE IF NOT EXISTS workspaces (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  dialect VARCHAR(64) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dialects (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(64) NOT NULL UNIQUE,
  label VARCHAR(128) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS completions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  category VARCHAR(32) NOT NULL,
  value VARCHAR(128) NOT NULL,
  dialect VARCHAR(64) NOT NULL,
  workspace_id INT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO dialects (code, label) VALUES
  ('sparksql', 'SparkSQL'),
  ('hive', 'HiveSQL');

INSERT INTO completions (category, value, dialect, workspace_id) VALUES
  ('keyword', 'SELECT', 'sparksql', NULL),
  ('keyword', 'FROM', 'sparksql', NULL),
  ('keyword', 'WHERE', 'sparksql', NULL),
  ('keyword', 'GROUP BY', 'sparksql', NULL),
  ('keyword', 'ORDER BY', 'sparksql', NULL),
  ('keyword', 'INSERT', 'sparksql', NULL),
  ('keyword', 'UPDATE', 'sparksql', NULL),
  ('keyword', 'DELETE', 'sparksql', NULL),
  ('function', 'COUNT', 'sparksql', NULL),
  ('function', 'SUM', 'sparksql', NULL),
  ('function', 'AVG', 'sparksql', NULL),
  ('keyword', 'SELECT', 'hive', NULL),
  ('keyword', 'FROM', 'hive', NULL),
  ('keyword', 'WHERE', 'hive', NULL),
  ('keyword', 'GROUP BY', 'hive', NULL),
  ('keyword', 'ORDER BY', 'hive', NULL),
  ('keyword', 'INSERT', 'hive', NULL),
  ('keyword', 'UPDATE', 'hive', NULL),
  ('keyword', 'DELETE', 'hive', NULL),
  ('function', 'COUNT', 'hive', NULL),
  ('function', 'SUM', 'hive', NULL),
  ('function', 'AVG', 'hive', NULL);
