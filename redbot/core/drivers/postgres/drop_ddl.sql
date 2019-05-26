SELECT config.delete_all_schemas();
DROP SCHEMA IF EXISTS config CASCADE;
DROP SCHEMA IF EXISTS jsonb_utils CASCADE;
DROP EVENT TRIGGER IF EXISTS red_drop_schema_trigger CASCADE;
