-- Session metadata tables use names chosen by the user in chat (validated by the orchestrator).
-- CREATE TABLE mirrors CSV headers as columns; example shape (your name and columns will differ):

/*
CREATE TABLE `my_glossary` (
  `Column_From_Csv_1` VARCHAR(512) NULL,
  `Column_From_Csv_2` TEXT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `my_glossary` (`Column_From_Csv_1`, `Column_From_Csv_2`) VALUES ('a', 'b');
*/
