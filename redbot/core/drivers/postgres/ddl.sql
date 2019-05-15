/*
 ************************************************************
 * PostgreSQL driver Data Definition Language (DDL) Script. *
 ************************************************************
 */


/*
 * Like `jsonb_set` but will insert new objects where one is missing along the path.
 */
CREATE OR REPLACE FUNCTION
  jsonb_set_deep(target jsonb, new_value jsonb, VARIADIC identifiers text[])
    RETURNS jsonb
    LANGUAGE plpgsql
  AS $$
  DECLARE
    cur_value_type text;
    idx integer := 1;
    num_identifiers CONSTANT integer := array_length(identifiers, 1);
  BEGIN
    LOOP
      IF idx = num_identifiers THEN
        RETURN jsonb_set(target, identifiers, new_value);
      ELSE
        cur_value_type := jsonb_typeof(target #> identifiers[:idx]);
        IF cur_value_type IS NULL THEN
          -- Parent key didn't exist in JSON before - insert new object
          target := jsonb_set(target, identifiers[:idx], '{}'::jsonb);
        ELSEIF cur_value_type != 'object' THEN
          -- We can't set the sub-field of a null, int, float, array etc.
          RAISE EXCEPTION 'Cannot set sub-field of %', cur_value_type
            USING ERRCODE = 'error_in_assignment';
        END IF;
      END IF;
      idx := idx + 1;
    END LOOP;
  END;
$$;


/*
 * Clear a key or sub-key from a JSONB object.
 *
 * This is simply an alias for the `#-` JSONB operator.
 */
CREATE OR REPLACE FUNCTION
  jsonb_clear(target jsonb, VARIADIC identifiers text[])
    RETURNS jsonb
    LANGUAGE SQL
  AS $$
    SELECT target #- identifiers;
$$;


/*
 * Like `jsonb_object_agg` but aggregates more than two columns into a
 * single JSONB object.
 *
 * If possible, use `jsonb_object_agg` instead for performance reasons.
 */
DROP AGGREGATE IF EXISTS jsonb_agg_all(json_data jsonb, VARIADIC primary_keys text[]);
CREATE AGGREGATE jsonb_agg_all(json_data jsonb, VARIADIC primary_keys text[]) (
  sfunc = jsonb_set_deep,
  stype = jsonb,
  initcond = '{}'
);


/*
 * Table to keep track of other cogs' schemas.
 */
CREATE TABLE IF NOT EXISTS red_cogs (
  cog_name text,
  cog_id text,
  schema_name text NOT NULL,
  PRIMARY KEY (cog_name, cog_id)
);


/*
 * Trigger for removing cog's entry from `red_cogs` table when schema is dropped.
 */
CREATE OR REPLACE FUNCTION
  red_drop_schema_trigger_function()
    RETURNS event_trigger
    LANGUAGE plpgsql
  AS $$
  DECLARE
    obj record;
  BEGIN
    FOR obj IN SELECT * FROM pg_event_trigger_dropped_objects() LOOP
      DELETE FROM red_cogs AS r WHERE r.schema_name = obj.object_name;
    END LOOP;
  END;
$$;
DROP EVENT TRIGGER IF EXISTS red_drop_schema_trigger;
CREATE EVENT TRIGGER red_drop_schema_trigger
  ON SQL_DROP
  WHEN TAG IN ('DROP SCHEMA')
  EXECUTE PROCEDURE red_drop_schema_trigger_function()
;
