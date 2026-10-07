\getenv migration_password DB_MIGRATION_PASSWORD
CREATE ROLE early_mind_migrator
    LOGIN PASSWORD :'migration_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS;

GRANT CONNECT ON DATABASE early_mind TO early_mind_migrator;
GRANT USAGE, CREATE ON SCHEMA public TO early_mind_migrator;

ALTER DEFAULT PRIVILEGES FOR ROLE early_mind_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO early_mind_app;
ALTER DEFAULT PRIVILEGES FOR ROLE early_mind_migrator IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO early_mind_app;
