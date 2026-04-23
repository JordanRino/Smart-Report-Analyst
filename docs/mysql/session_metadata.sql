-- Metadata tables are created dynamically by the metadata updater from each CSV:
-- CREATE TABLE `md_<team>_<threadid>` ( <one column per CSV header>, ... ) + INSERT rows.
-- There is no fixed global `session_metadata` schema required for the CSV-mirror flow.
--
-- Example only (replace header names and types with your file):

/*
CREATE TABLE `md_wlr_examplethreadid` (
  `column_from_csv_1` VARCHAR(512) NULL,
  `column_from_csv_2` TEXT NULL,
  `amount` DECIMAL(20,4) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `md_wlr_examplethreadid` (`column_from_csv_1`, `column_from_csv_2`, `amount`)
VALUES
  ('row1col1', 'row1col2', 123.45),
  ('row2col1', 'row2col2', 678.00);
*/
