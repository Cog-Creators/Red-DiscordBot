DROP FUNCTION IF EXISTS jsonb_set_deep(target jsonb, new_value jsonb, VARIADIC identifiers text[]);
DROP FUNCTION IF EXISTS jsonb_clear(target jsonb, VARIADIC identifiers text[]);
DROP AGGREGATE IF EXISTS jsonb_agg_all(json_data jsonb, VARIADIC primary_keys text[]);
DROP TABLE IF EXISTS red_cogs;
DROP FUNCTION IF EXISTS red_drop_schema_trigger_function();
DROP EVENT TRIGGER IF EXISTS red_drop_schema_trigger;
