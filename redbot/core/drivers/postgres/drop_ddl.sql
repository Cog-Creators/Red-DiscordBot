SELECT red_config.delete_all_schemas();
DROP SCHEMA IF EXISTS red_config CASCADE;
DROP SCHEMA IF EXISTS red_utils CASCADE;
DROP EVENT TRIGGER IF EXISTS red_drop_schema_trigger CASCADE;
