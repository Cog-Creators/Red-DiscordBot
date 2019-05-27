/*
 ************************************************************
 * PostgreSQL driver Data Definition Language (DDL) Script. *
 ************************************************************
 */

CREATE SCHEMA IF NOT EXISTS red_config;
CREATE SCHEMA IF NOT EXISTS red_utils;

CREATE OR REPLACE FUNCTION
  red_config.maybe_create_table(
    cog_name text,
    cog_id text,
    config_category text,
    pkey_len integer,
    pkey_type text
  )
    RETURNS void
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', cog_name, cog_id);
    schema_exists boolean := (
      SELECT EXISTS (
        SELECT 1
        FROM red_config.red_cogs t
        WHERE t.cog_name = $1 AND t.cog_id = $2
      )
    );
    table_exists boolean := schema_exists AND (
      SELECT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = schemaname AND table_name = config_category
      )
    );
  BEGIN
    IF NOT schema_exists THEN
      PERFORM red_config.create_schema(cog_name, cog_id);
    END IF;
    IF NOT table_exists THEN
      PERFORM red_config.create_table(schemaname, config_category, pkey_len, pkey_type);
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  red_config.create_schema(new_cog_name text, new_cog_id text, OUT schemaname text)
    RETURNS text
    LANGUAGE 'plpgsql'
  AS $$
  BEGIN
    schemaname := concat_ws('.', new_cog_name, new_cog_id);
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', schemaname);
    INSERT INTO red_config.red_cogs AS t VALUES(new_cog_name, new_cog_id, schemaname)
    ON CONFLICT(cog_name, cog_id) DO UPDATE SET
        schemaname = excluded.schemaname
    ;
  END;
$$;


CREATE OR REPLACE FUNCTION
  red_config.create_table(schemaname text, config_category text, pkey_len integer, pkey_type text)
    RETURNS void
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    pkey_columns text;
    pkey_column_definitions text;
    constraintname text := config_category||'_pkey';
  BEGIN
    SELECT red_utils.gen_pkey_column_definitions(1, pkey_len, pkey_type)
    INTO pkey_column_definitions;

    SELECT red_utils.gen_pkey_columns(1, pkey_len) INTO pkey_columns;

    EXECUTE format($query$
      CREATE TABLE IF NOT EXISTS %I.%I (
        %s,
        json_data jsonb DEFAULT '{}' NOT NULL,
        CONSTRAINT %I PRIMARY KEY (%s)
      )
      $query$,
      schemaname,
      config_category,
      pkey_column_definitions,
      constraintname,
      pkey_columns
    );
  END;
$$;


CREATE OR REPLACE FUNCTION
  red_config.get(
    cog_name text,
    cog_id text,
    config_category text,
    pkey_len integer,
    pkeys anyarray,
    identifiers text[] DEFAULT '{}',
    OUT result jsonb
  )
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', cog_name, cog_id);
    whereclause text;
    num_pkeys CONSTANT integer := coalesce(array_length(pkeys, 1), 0);
    num_missing_pkeys CONSTANT integer :=  pkey_len - num_pkeys;
    missing_pkey_columns text;
  BEGIN
    SELECT red_utils.gen_whereclause(num_pkeys) INTO whereclause;

    IF num_missing_pkeys <= 0 THEN
      -- No missing primary keys: we're getting all or part of a document.
      EXECUTE
        format(
          'SELECT json_data #> $2 FROM %I.%I WHERE %s',
          schemaname,
          config_category,
          whereclause
        )
        INTO result
        USING pkeys, identifiers;

    ELSIF num_missing_pkeys = 1 THEN
      -- 1 missing primary key: we can use the built-in jsonb_object_agg() aggregate function.
      EXECUTE
        format(
          'SELECT jsonb_object_agg(%I::text, json_data) FROM %I.%I WHERE %s',
          'primary_key_'||pkey_len,
          schemaname,
          config_category,
          whereclause
        )
        INTO result
        USING pkeys;
    ELSE
      -- Multiple missing primary keys: we must use our custom red_utils.jsonb_object_agg2()
      -- aggregate function.
      SELECT red_utils.gen_pkey_columns_casted(num_pkeys + 1, pkey_len) INTO missing_pkey_columns;

      EXECUTE
        format(
          'SELECT red_utils.jsonb_object_agg2(json_data, %s) FROM %I.%I WHERE %s',
          missing_pkey_columns,
          schemaname,
          config_category,
          whereclause
        )
        INTO result
        USING pkeys;
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  red_config.set(
    cog_name text,
    cog_id text,
    config_category text,
    new_value jsonb,
    pkey_len integer,
    pkey_type text,
    pkeys anyarray,
    identifiers text[] DEFAULT '{}'
  )
    RETURNS void
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', cog_name, cog_id);
    pkey_placeholders text;
    new_document jsonb := red_utils.jsonb_set2('{}', new_value, VARIADIC identifiers);
    constraintname text := config_category||'_pkey';
    num_pkeys CONSTANT integer := coalesce(array_length(pkeys, 1), 0);
    num_missing_pkeys CONSTANT integer := pkey_len - num_pkeys;
    pkey_column_definitions text;
    whereclause text;
    missing_pkey_columns text;
  BEGIN
    PERFORM red_config.maybe_create_table(cog_name, cog_id, config_category, pkey_len, pkey_type);

    SELECT red_utils.gen_pkey_placeholders(num_pkeys, pkey_type) INTO pkey_placeholders;

    IF num_missing_pkeys = 0 THEN
      -- Setting all or part of a document
      EXECUTE format($query$
        INSERT INTO %I.%I AS t VALUES (%s, $2)
        ON CONFLICT ON CONSTRAINT %I DO UPDATE
        SET
          json_data = red_utils.jsonb_set2(t.json_data, $3, VARIADIC $4)
        $query$,
        schemaname,
        config_category,
        pkey_placeholders,
        constraintname
        ) USING pkeys, new_document, new_value, identifiers;

    ELSE
      -- Setting multiple documents
      SELECT red_utils.gen_whereclause(num_pkeys) INTO whereclause;

      -- Delete all documents which we're setting first, since we don't know whether they'll be
      -- replaced by the subsequent INSERT.
      EXECUTE format($query$
          DELETE FROM %I.%I WHERE %s
        $query$,
        schemaname,
        config_category,
        whereclause
      ) USING pkeys;

      SELECT red_utils.gen_pkey_columns_casted(num_pkeys + 1, pkey_len, pkey_type)
      INTO missing_pkey_columns;

      SELECT red_utils.gen_pkey_column_definitions(start := num_pkeys + 1, stop := pkey_len)
      INTO pkey_column_definitions;

      -- Insert all new documents
      EXECUTE format($query$
          INSERT INTO %I.%I AS t
            SELECT %s, json_data
            FROM red_utils.generate_rows_from_object($2, $3) AS f(%s, json_data jsonb)
          ON CONFLICT ON CONSTRAINT %I DO UPDATE
          SET
            json_data = excluded.json_data
        $query$,
        schemaname,
        config_category,
        concat_ws(', ', pkey_placeholders, missing_pkey_columns),
        pkey_column_definitions,
        constraintname
      ) USING pkeys, new_value, num_missing_pkeys;
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  red_config.clear(
    cog_name text,
    cog_id text,
    config_category text,
    pkeys anyarray,
    identifiers text[] DEFAULT '{}'
  )
    RETURNS void
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', cog_name, cog_id);
    num_pkeys CONSTANT integer := coalesce(array_length(pkeys, 1), 0);
    num_identifiers CONSTANT integer := coalesce(array_length(identifiers, 1), 0);
    whereclause text;
  BEGIN
    SELECT red_utils.gen_whereclause(num_pkeys) INTO whereclause;

    IF num_identifiers > 0 THEN
      -- Popping a key from a document or nested document.
      EXECUTE format($query$
          UPDATE %I.%I AS t
          SET
            json_data = t.json_data #- $2
          WHERE %s
        $query$,
        schemaname,
        config_category,
        whereclause
      ) USING pkeys, identifiers;

    ELSIF num_pkeys > 0 THEN
      -- Deleting one or many documents
      EXECUTE format($query$
          DELETE FROM %I.%I WHERE %s
        $query$,
        schemaname,
        config_category,
        whereclause
      ) USING pkeys;

    ELSIF config_category != '' THEN
      -- Deleting an entire category
      EXECUTE format($query$
          DROP TABLE %I.%I CASCADE
        $query$,
        schemaname,
        config_category
      );

    ELSE
      -- Deleting an entire cog's data
      EXECUTE format($query$
          DROP SCHEMA %I CASCADE
        $query$,
        schemaname
      );
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  red_config.inc(
    cog_name text,
    cog_id text,
    config_category text,
    amount numeric,
    default_value numeric,
    pkey_len integer,
    pkey_type text,
    pkeys anyarray,
    identifiers text[] DEFAULT '{}',
    OUT result numeric
  )
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', cog_name, cog_id);
    pkey_placeholders text;
    num_identifiers CONSTANT integer := coalesce(array_length(identifiers, 1), 0);
    existing_document jsonb;
    existing_value jsonb;
    new_document jsonb;
    whereclause text;
  BEGIN
    IF num_identifiers = 0 THEN
      -- Without identifiers, there's no chance we're actually incrementing a number
      RAISE EXCEPTION 'Cannot increment document(s)'
        USING ERRCODE = 'wrong_object_type';
    END IF;

    PERFORM red_config.maybe_create_table(cog_name, cog_id, config_category, pkey_len, pkey_type);

    SELECT red_utils.gen_whereclause(pkey_len) INTO whereclause;

    -- Look for the existing document
    EXECUTE format(
        'SELECT json_data FROM %I.%I WHERE %s',
        schemaname,
        config_category,
        whereclause
      ) INTO existing_document USING pkeys;

    IF existing_document IS NULL THEN
      -- We need to insert a new document
      new_document := red_utils.jsonb_set2('{}', default_value + amount, VARIADIC identifiers);
      SELECT red_utils.gen_pkey_placeholders(pkey_len, pkey_type) INTO pkey_placeholders;

      EXECUTE format(
        'INSERT INTO %I.%I VALUES(%s, $2)',
        schemaname,
        config_category,
        pkey_placeholders
        ) USING pkeys, new_document;
      result := default_value + amount;

    ELSE
      -- We need to update the existing document
      existing_value := existing_document #> identifiers;
      IF existing_value IS NULL THEN
        result := default_value + amount;
        new_document := red_utils.jsonb_set2(existing_document, to_jsonb(result), identifiers);
      ELSIF jsonb_typeof(existing_value) != 'number' THEN
        RAISE EXCEPTION 'Cannot increment non-numeric value %', existing_value
          USING ERRCODE = 'wrong_object_type';
      ELSE
        result := existing_value::text::numeric + amount;
        new_document := red_utils.jsonb_set2(existing_document, to_jsonb(result), identifiers);
      END IF;

      EXECUTE format(
        'UPDATE %I.%I SET json_data = $2 WHERE %s',
        schemaname,
        config_category,
        whereclause
        ) USING pkeys, new_document;
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  /*
   * Toggle a boolean within a JSONB object.
   *
   * If the value doesn't already exist, it is inserted as `NOT
   * default_value`.
   *
   * Raises 'wrong_object_type' error when trying to toggle a
   * non-boolean value.
   */
  red_config.toggle(
    cog_name text,
    cog_id text,
    config_category text,
    default_value boolean,
    pkey_len integer,
    pkey_type text,
    pkeys anyarray,
    identifiers text[] DEFAULT '{}',
    OUT result boolean
  )
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', cog_name, cog_id);
    pkey_placeholders text;
    num_identifiers CONSTANT integer := coalesce(array_length(identifiers, 1), 0);
    existing_document jsonb;
    existing_value jsonb;
    new_document jsonb;
    whereclause text;
  BEGIN
    IF num_identifiers = 0 THEN
      -- Without identifiers, there's no chance we're actually toggling a boolean
      RAISE EXCEPTION 'Cannot increment document(s)'
        USING ERRCODE = 'wrong_object_type';
    END IF;

    PERFORM red_config.maybe_create_table(cog_name, cog_id, config_category, pkey_len, pkey_type);

    SELECT red_utils.gen_whereclause(pkey_len) INTO whereclause;

    -- Look for the existing document
    EXECUTE format(
        'SELECT json_data FROM %I.%I WHERE %s',
        schemaname,
        config_category,
        whereclause
      ) INTO existing_document USING pkeys;

    IF existing_document IS NULL THEN
      -- We need to insert a new document
      new_document := red_utils.jsonb_set2('{}', NOT default_value, VARIADIC identifiers);
      SELECT red_utils.gen_pkey_placeholders(pkey_len, pkey_type) INTO pkey_placeholders;

      EXECUTE format(
        'INSERT INTO %I.%I VALUES(%s, $2)',
        schemaname,
        config_category,
        pkey_placeholders
        ) USING pkeys, new_document;
      SELECT NOT default_value INTO result;

    ELSE
      -- We need to update the existing document
      existing_value := existing_document #> identifiers;
      IF existing_value IS NULL THEN
        SELECT NOT default_value INTO result;
        new_document := red_utils.jsonb_set2(existing_document, to_jsonb(result), identifiers);
      ELSIF jsonb_typeof(existing_value) != 'boolean' THEN
        RAISE EXCEPTION 'Cannot increment non-boolean value %', existing_value
          USING ERRCODE = 'wrong_object_type';
      ELSE
        SELECT NOT existing_value::text::boolean INTO result;
        new_document := red_utils.jsonb_set2(existing_document, to_jsonb(result), identifiers);
      END IF;

      EXECUTE format(
        'UPDATE %I.%I SET json_data = $2 WHERE %s',
        schemaname,
        config_category,
        whereclause
        ) USING pkeys, new_document;
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  /*
   * Delete all schemas listed in the red_config.red_cogs table.
   */
  red_config.delete_all_schemas()
    RETURNS void
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    cog_entry record;
  BEGIN
    FOR cog_entry IN SELECT * FROM red_config.red_cogs t LOOP
      EXECUTE format('DROP SCHEMA %I CASCADE', cog_entry.schemaname);
    END LOOP;
  END;
$$;



CREATE OR REPLACE FUNCTION
  /*
   * Like `jsonb_set` but will insert new objects where one is missing along the path.
   */
  red_utils.jsonb_set2(target jsonb, new_value jsonb, VARIADIC identifiers text[])
    RETURNS jsonb
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    cur_value_type text;
    idx integer := 1;
    num_identifiers CONSTANT integer := coalesce(array_length(identifiers, 1), 0);
  BEGIN
    IF num_identifiers = 0 THEN
      RETURN new_value;
    END IF;
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


CREATE OR REPLACE FUNCTION
  /*
   * Return a set of rows to insert into a table, from a single JSONB
   * object containing multiple documents.
   */
  red_utils.generate_rows_from_object(object jsonb, num_missing_pkeys integer)
    RETURNS setof record
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    pair record;
    column_definitions text;
  BEGIN
    IF num_missing_pkeys = 1 THEN
      -- Base case: Simply return (key, value) pairs
      RETURN QUERY
        SELECT key AS key_1, value AS json_data
        FROM jsonb_each(object);
    ELSE
      -- We need to return (key, key, ..., value) pairs: recurse into inner JSONB objects
      SELECT red_utils.gen_pkey_column_definitions(start := 2, stop := num_missing_pkeys)
      INTO column_definitions;

      FOR pair IN SELECT * FROM jsonb_each(object) LOOP
        RETURN QUERY EXECUTE format($query$
            SELECT $1 AS key_1, *
            FROM red_utils.generate_rows_from_object($2, $3)
              AS f(%s, json_data jsonb)
          $query$,
          column_definitions
          ) USING pair.key, pair.value, num_missing_pkeys - 1;
      END LOOP;
    END IF;
    RETURN;
  END;
$$;


CREATE OR REPLACE FUNCTION
  /*
   * Get a comma-separated list of primary key placeholders.
   *
   * The placeholder will always be $1. Particularly useful for
   * inserting values into a table from an array of primary keys.
   */
  red_utils.gen_pkey_placeholders(num_pkeys integer, pkey_type text DEFAULT 'text')
    RETURNS text
    LANGUAGE 'sql'
  AS $$
    SELECT string_agg(t.item, ', ')
    FROM (
      SELECT format('$1[%s]::%s', idx, pkey_type) AS item
      FROM generate_series(1, num_pkeys) idx) t
    ;
$$;

CREATE OR REPLACE FUNCTION
  /*
   * Generate a whereclause for the given number of primary keys.
   *
   * When there are no primary keys, this will simply return the the
   * string 'TRUE'. When there are multiple, it will return multiple
   * equality comparisons concatenated with 'AND'.
   */
  red_utils.gen_whereclause(num_pkeys integer)
    RETURNS text
    LANGUAGE 'sql'
  AS $$
    SELECT coalesce(string_agg(t.item, ' AND '), 'TRUE')
    FROM (
      SELECT format('%I = $1[%s]', 'primary_key_'||idx, idx) AS item
      FROM generate_series(1, num_pkeys) idx) t
    ;
$$;

CREATE OR REPLACE FUNCTION
  /*
   * Generate a column definition list.
   */
  red_utils.gen_pkey_columns(start integer, stop integer)
    RETURNS text
    LANGUAGE 'sql'
  AS $$
    SELECT string_agg(t.item, ', ')
    FROM (
      SELECT quote_ident('primary_key_'||idx) AS item
      FROM generate_series(start, stop) idx) t
    ;
$$;

CREATE OR REPLACE FUNCTION
  /*
   * Generate a column definition list.
   */
  red_utils.gen_pkey_columns_casted(start integer, stop integer, pkey_type text DEFAULT 'text')
    RETURNS text
    LANGUAGE 'sql'
  AS $$
    SELECT string_agg(t.item, ', ')
    FROM (
      SELECT format('%I::%s', 'primary_key_'||idx, pkey_type) AS item
      FROM generate_series(start, stop) idx) t
    ;
$$;


CREATE OR REPLACE FUNCTION
  /*
   * Generate a column definition list.
   */
  red_utils.gen_pkey_column_definitions(
    start integer, stop integer, column_type text DEFAULT 'text'
  )
    RETURNS text
    LANGUAGE 'sql'
  AS $$
    SELECT string_agg(t.item, ', ')
    FROM (
      SELECT format('%I %s', 'primary_key_'||idx, column_type) AS item
      FROM generate_series(start, stop) idx) t
    ;
$$;


DROP AGGREGATE IF EXISTS red_utils.jsonb_object_agg2(jsonb, VARIADIC text[]);
CREATE AGGREGATE
  /*
   * Like `jsonb_object_agg` but aggregates more than two columns into a
   * single JSONB object.
   *
   * If possible, use `jsonb_object_agg` instead for performance reasons.
   */
  red_utils.jsonb_object_agg2(json_data jsonb, VARIADIC primary_keys text[]) (
    sfunc = red_utils.jsonb_set2,
    stype = jsonb,
    initcond = '{}'
  )
;


CREATE TABLE IF NOT EXISTS
  /*
   * Table to keep track of other cogs' schemas.
   */
  red_config.red_cogs(
    cog_name text,
    cog_id text,
    schemaname text NOT NULL,
    PRIMARY KEY (cog_name, cog_id)
)
;


CREATE OR REPLACE FUNCTION
  /*
   * Trigger for removing cog's entry from `red_config.red_cogs` table when schema is dropped.
   */
  red_config.drop_schema_trigger_function()
    RETURNS event_trigger
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    obj record;
  BEGIN
    FOR obj IN SELECT * FROM pg_event_trigger_dropped_objects() LOOP
      DELETE FROM red_config.red_cogs AS r WHERE r.schemaname = obj.object_name;
    END LOOP;
  END;
$$;
DROP EVENT TRIGGER IF EXISTS red_drop_schema_trigger;
CREATE EVENT TRIGGER red_drop_schema_trigger
  ON SQL_DROP
  WHEN TAG IN ('DROP SCHEMA')
  EXECUTE PROCEDURE red_config.drop_schema_trigger_function()
;
