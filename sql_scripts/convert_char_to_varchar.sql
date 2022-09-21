-- Update the database name to the one you are working with
SET @database = "DATABASE_NAME";

-- Modify Column Script
-- The result will be an alter script with each table and columns that need to be altered.
-- At the end of each alter script will be the updae to Aria with PAGE_CHECKSUM=1, row_format=PAGE and transactional=0
WITH combo_column AS (
	SELECT @database AS "TABLE_SCHEMA", a.TABLE_NAME AS "mod_table", a.TABLE_TYPE, b.DATA_TYPE,b.COLUMN_NAME,b.COLUMN_TYPE, b.COLUMN_DEFAULT,
	GROUP_CONCAT(
	CONCAT(" MODIFY COLUMN `",b.COLUMN_NAME,"` ",'var', b.COLUMN_TYPE, " CHARACTER SET latin1 COLLATE latin1_swedish_ci DEFAULT ", IF(b.COLUMN_DEFAULT IS NULL, "NULL", b.COLUMN_DEFAULT))
	SEPARATOR ",") AS "column_update"
	FROM information_schema.`TABLES` a INNER JOIN information_schema.`COLUMNS` b
		ON a.TABLE_NAME = b.TABLE_NAME
			AND a.TABLE_SCHEMA = b.TABLE_SCHEMA
	WHERE a.TABLE_SCHEMA=@database
		AND a.TABLE_SCHEMA = b.TABLE_SCHEMA
		AND a.TABLE_TYPE<>'VIEW'
		AND b.DATA_TYPE LIKE 'char%'
	GROUP BY a.TABLE_NAME
	),
	-- This gets all tables which are not yet Aria
	to_aria AS (
	SELECT @database AS "TABLE_SCHEMA", TABLE_NAME AS "mod_table", TABLE_TYPE, `TABLES`.`ENGINE`, CONCAT("ENGINE = Aria row_format=PAGE page_checksum=1 TRANSACTIONAL=0") AS "to_aria_engine"
	FROM information_schema.`TABLES`
	WHERE `TABLES`.TABLE_SCHEMA=@database
		AND (`TABLES`.`ENGINE`<>'Aria'
			OR `TABLES`.`ENGINE`='Myisam'))

-- Result will be a script to copy/paste to make change for CHAR to VAR and update to Aria engine
-- If NULL result, then there is no update needed
SELECT a.TABLE_NAME,
	
	CONCAT("ALTER TABLE ",@database,".`",a.TABLE_NAME,"` ",
	IFNULL(CONCAT(c.column_update, ", "), ""),
	IFNULL(d.to_aria_engine, ""),
	"; OPTIMIZE TABLE ",@database,".`", a.TABLE_NAME,"`;") AS "Alter_Script"
	
FROM information_schema.`TABLES` a INNER JOIN information_schema.`COLUMNS` b
	ON a.TABLE_NAME = b.TABLE_NAME
		AND a.TABLE_SCHEMA = b.TABLE_SCHEMA
		LEFT JOIN combo_column c
			ON a.TABLE_NAME = c.mod_table
				AND a.TABLE_SCHEMA = c.TABLE_SCHEMA
					LEFT JOIN to_aria d
						ON a.TABLE_NAME = d.mod_table
						 AND a.TABLE_SCHEMA = d.TABLE_SCHEMA

WHERE a.TABLE_SCHEMA=@database
	AND ((a.TABLE_NAME = c.mod_table AND a.TABLE_SCHEMA = c.TABLE_SCHEMA) OR (a.TABLE_NAME = d.mod_table AND a.TABLE_SCHEMA = d.TABLE_SCHEMA))
GROUP BY a.TABLE_NAME;

-- Check if missed any Char to Var
SELECT * FROM information_schema.`COLUMNS` WHERE TABLE_SCHEMA = @database AND COLUMN_TYPE LIKE 'char%';

-- Check if missed any conversion to Aria
SELECT CONCAT('ALTER TABLE ',@database,'.',`TABLES`.TABLE_NAME,' ENGINE = Aria row_format=PAGE page_checksum=1 TRANSACTIONAL=0; OPTIMIZE TABLE ',@database,".`",`TABLES`.TABLE_NAME,"`;") AS "To convert to Aria"
FROM information_schema.`TABLES`
WHERE `TABLES`.TABLE_SCHEMA=@database and `TABLES`.`ENGINE`='Myisam' 
ORDER BY `TABLES`.DATA_LENGTH ASC;