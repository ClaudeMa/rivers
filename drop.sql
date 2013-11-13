--- relations table
DROP TYPE IF EXISTS reltype CASCADE;
DROP TABLE IF EXISTS relations CASCADE;
--- tributaries table
DROP TABLE IF EXISTS tributaries;
--- waysinrel table
DROP TABLE IF EXISTS waysinrel;
--- ways table
DROP TYPE IF EXISTS waytype CASCADE;

DROP TABLE IF EXISTS ways CASCADE;
DROP TRIGGER IF EXISTS waysdrop ON ways;
--- nodesinway table
DROP TABLE IF EXISTS nodesinway;
DROP TRIGGER IF EXISTS nodesinwaydrop ON nodesinway;
--- nodes table
DROP TABLE IF EXISTS nodes;
DROP TRIGGER IF EXISTS nodesdrop ON nodes;
