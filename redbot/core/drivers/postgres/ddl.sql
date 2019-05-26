/*
 ************************************************************
 * PostgreSQL driver Data Definition Language (DDL) Script. *
 ************************************************************
 */

CREATE SCHEMA IF NOT EXISTS config;
CREATE SCHEMA IF NOT EXISTS jsonb_utils;

CREATE OR REPLACE FUNCTION
  config.maybe_create_table(
    cog_name text,
    cog_id text,
    config_category text,
    pkey_len integer,
    pkey_type text
  )
    RETURNS void
    LANGUAGE plpgsql
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', cog_name, cog_id);
    schema_exists boolean := (
      SELECT EXISTS (
        SELECT 1
        FROM config.red_cogs t
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
      PERFORM config.create_schema(cog_name, cog_id);
    END IF;
    IF NOT table_exists THEN
      PERFORM config.create_table(schemaname, config_category, pkey_len, pkey_type);
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  config.create_schema(new_cog_name text, new_cog_id text, OUT schemaname text)
    RETURNS text
    LANGUAGE plpgsql
  AS $$
  BEGIN
    schemaname := concat_ws('.', new_cog_name, new_cog_id);
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', schemaname);
    INSERT INTO config.red_cogs AS t VALUES(new_cog_name, new_cog_id, schemaname)
      ON CONFLICT(cog_name, cog_id) DO UPDATE SET
        schemaname = excluded.schemaname
    ;
  END;
$$;


CREATE OR REPLACE FUNCTION
  config.create_table(schemaname text, config_category text, pkey_len integer, pkey_type text)
    RETURNS void
    LANGUAGE plpgsql
  AS $$
  DECLARE
    pkeys text[] := '{}'::text[];
    pkey_declarations text[] := '{}'::text[];
    constraintname text := config_category||'_pkey';
    idx integer;
  BEGIN
    FOR idx IN SELECT generate_series(1, pkey_len) LOOP
      SELECT
        array_append(pkey_declarations, format('%I %s', 'primary_key_'||idx, pkey_type))
        INTO pkey_declarations;
      SELECT
        array_append(pkeys, quote_ident('primary_key_'||idx))
        INTO pkeys;
    END LOOP;
    EXECUTE format($query$
      CREATE TABLE IF NOT EXISTS %I.%I (
        %s,
        json_data jsonb DEFAULT '{}' NOT NULL,
        CONSTRAINT %I PRIMARY KEY (%s)
      )
      $query$,
      schemaname,
      config_category,
      array_to_string(pkey_declarations, ', '),
      constraintname,
      array_to_string(pkeys, ', ')
    );
  END;
$$;


CREATE OR REPLACE FUNCTION
  config.get(
    cog_name text,
    cog_id text,
    config_category text,
    pkey_len integer,
    pkeys anyarray,
    identifiers text[] DEFAULT '{}',
    OUT result jsonb
  )
    LANGUAGE plpgsql
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', cog_name, cog_id);
    where_conditions text[] := '{}'::text[];
    whereclause text;
    num_pkeys CONSTANT integer := coalesce(array_length(pkeys, 1), 0);
    num_missing_pkeys CONSTANT integer :=  pkey_len - num_pkeys;
    missing_pkey_columns text[] := '{}';
    idx integer;
  BEGIN
    FOR idx IN SELECT generate_series(1, num_pkeys) LOOP
      SELECT
        array_append(where_conditions, format('%I = $2[%s]', 'primary_key_'||idx, idx))
        INTO where_conditions;
    END LOOP;
    IF num_missing_pkeys <= 0 THEN
      -- No missing primary keys: we're getting all or part of a document.
      EXECUTE
        format(
          'SELECT json_data #> $1 FROM %I.%I WHERE %s',
          schemaname,
          config_category,
          array_to_string(where_conditions, ' AND ')
        )
        INTO result
        USING identifiers, pkeys;
    ELSIF num_missing_pkeys = 1 THEN
      -- 1 missing primary key: we can use the built-in jsonb_object_agg() aggregate function.
      IF pkey_len = 1 THEN
        whereclause := '';
      ELSE
        whereclause := ' WHERE '||array_to_string(where_conditions, ' AND ');
      END IF;
      EXECUTE
        format(
          'SELECT jsonb_object_agg(%I::text, json_data) FROM %I.%I'||whereclause,
          'primary_key_'||pkey_len,
          schemaname,
          config_category
        )
        INTO result
        USING identifiers, pkeys;
    ELSE
      -- Multiple missing primary keys: we must use our custom jsonb_utils.agg_many() aggregate function.
      FOR idx IN SELECT generate_series(num_pkeys + 1, pkey_len) LOOP
        SELECT
          array_append(missing_pkey_columns, format('%I::text', 'primary_key_'||idx))
          INTO missing_pkey_columns;
      END LOOP;
      IF num_missing_pkeys < pkey_len THEN
        whereclause := ' WHERE '||array_to_string(where_conditions, ' AND ');
      ELSE
        whereclause := '';
      END IF;
      EXECUTE
        format(
          'SELECT jsonb_utils.agg_many(json_data, %s) FROM %I.%I'||whereclause,
          array_to_string(missing_pkey_columns, ', '),
          schemaname,
          config_category
        )
        INTO result
        USING identifiers, pkeys;
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  config.set(
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
    LANGUAGE plpgsql
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', cog_name, cog_id);
    pkey_placeholders text[] := '{}'::text[];
    idx integer;
    new_document jsonb := jsonb_utils.set('{}', new_value, VARIADIC identifiers);
    constraintname text := config_category||'_pkey';
    num_pkeys CONSTANT integer := coalesce(array_length(pkeys, 1), 0);
    num_missing_pkeys CONSTANT integer := pkey_len - num_pkeys;
    column_definition_list text[] := '{}';
    where_conditions text[] := '{}';
  BEGIN
    PERFORM config.maybe_create_table(cog_name, cog_id, config_category, pkey_len, pkey_type);
    IF num_missing_pkeys = 0 THEN
      FOR idx IN SELECT generate_series(1, num_pkeys) LOOP
        SELECT
          array_append(pkey_placeholders, format('$1[%s]::%s', idx, pkey_type))
          INTO pkey_placeholders;
      END LOOP;
      EXECUTE format($query$
        INSERT INTO %I.%I AS t
          VALUES (%s, $2)
          ON CONFLICT ON CONSTRAINT %I DO UPDATE SET
            json_data = jsonb_utils.set(t.json_data, $3, VARIADIC $4)
        $query$,
        schemaname,
        config_category,
        array_to_string(pkey_placeholders, ', '),
        constraintname
        ) USING pkeys, new_document, new_value, identifiers;
    ELSE
      FOR idx IN SELECT generate_series(1, num_pkeys) LOOP
        SELECT
          array_append(pkey_placeholders,
                       format('$1[%s]::%s AS %I', idx, pkey_type, 'primary_key_'||idx))
          INTO pkey_placeholders;
        SELECT
          array_append(where_conditions, format('%I = $1[%s]', 'primary_key_'||idx, idx))
          INTO where_conditions;
      END LOOP;
      FOR idx IN SELECT generate_series(num_pkeys + 1, pkey_len) LOOP
        SELECT
          array_append(pkey_placeholders, format('%I::%s', 'primary_key_'||idx, pkey_type))
          INTO pkey_placeholders;
        SELECT
          array_append(column_definition_list, format('%I text', 'primary_key_'||idx))
          INTO column_definition_list;
      END LOOP;
      EXECUTE format($query$
          DELETE FROM %I.%I WHERE %s
        $query$,
        schemaname,
        config_category,
        CASE num_pkeys WHEN 0 THEN 'true' ELSE array_to_string(where_conditions, ' AND ') END
      ) USING pkeys;
      EXECUTE format($query$
          INSERT INTO %I.%I AS t
            SELECT %s, json_data FROM jsonb_utils.generate_rows_from_object($2, $3) AS f(%s, json_data jsonb)
            ON CONFLICT ON CONSTRAINT %I DO UPDATE SET
              json_data = excluded.json_data
        $query$,
        schemaname,
        config_category,
        array_to_string(pkey_placeholders, ', '),
        array_to_string(column_definition_list, ', '),
        constraintname
      ) USING pkeys, new_value, num_missing_pkeys;
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  config.clear(
    cog_name text,
    cog_id text,
    config_category text,
    pkeys anyarray,
    identifiers text[] DEFAULT '{}'
  )
    RETURNS void
    LANGUAGE plpgsql
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', cog_name, cog_id);
    idx integer;
    num_pkeys CONSTANT integer := coalesce(array_length(pkeys, 1), 0);
    num_identifiers CONSTANT integer := coalesce(array_length(identifiers, 1), 0);
    where_conditions text[] := '{}';
  BEGIN
    FOR idx IN SELECT generate_series(1, num_pkeys) LOOP
      SELECT
        array_append(where_conditions, format('%I = $1[%s]', 'primary_key_'||idx, idx))
        INTO where_conditions;
    END LOOP;
    IF num_identifiers > 0 THEN
      EXECUTE format($query$
          UPDATE %I.%I AS t SET
            json_data = t.json_data #- $2
          WHERE %s
        $query$,
        schemaname,
        config_category,
        array_to_string(where_conditions, ' AND ')
      ) USING pkeys, identifiers;
    ELSIF num_pkeys > 0 THEN
      EXECUTE format($query$
          DELETE FROM %I.%I WHERE %s
        $query$,
        schemaname,
        config_category,
        array_to_string(where_conditions, ' AND ')
      ) USING pkeys;
    ELSIF config_category != '' THEN
      EXECUTE format($query$
          DROP TABLE %I.%I CASCADE
        $query$,
        schemaname,
        config_category
      );
    ELSE
      EXECUTE format($query$
          DROP SCHEMA %I CASCADE
        $query$,
        schemaname
      );
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  config.inc(
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
    LANGUAGE plpgsql
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', cog_name, cog_id);
    pkey_placeholders text[] := '{}'::text[];
    idx integer;
    num_identifiers CONSTANT integer := coalesce(array_length(identifiers, 1), 0);
    existing_document jsonb;
    existing_value jsonb;
    new_document jsonb;
    where_conditions text[] := '{}';
    whereclause text;
  BEGIN
    PERFORM config.maybe_create_table(cog_name, cog_id, config_category, pkey_len, pkey_type);
    IF num_identifiers > 0 THEN
      FOR idx IN SELECT generate_series(1, pkey_len) LOOP
        SELECT
          array_append(where_conditions, format('%I = $1[%s]', 'primary_key_'||idx, idx))
          INTO where_conditions;
      END LOOP;
      whereclause := array_to_string(where_conditions, ' AND ');
      EXECUTE format(
          'SELECT json_data FROM %I.%I WHERE %s',
          schemaname,
          config_category,
          whereclause
        ) INTO existing_document USING pkeys;
      IF existing_document IS NULL THEN
        new_document := jsonb_utils.set('{}', default_value + amount, VARIADIC identifiers);
        FOR idx IN SELECT generate_series(1, pkey_len) LOOP
          SELECT
            array_append(pkey_placeholders, format('$1[%s]::%s', idx, pkey_type))
            INTO pkey_placeholders;
        END LOOP;
        EXECUTE format(
          'INSERT INTO %I.%I VALUES(%s, $2)',
          schemaname,
          config_category,
          array_to_string(pkey_placeholders, ', ')
          ) USING pkeys, new_document;
        result := default_value + amount;
      ELSE
        existing_value := existing_document #> identifiers;
        IF existing_value IS NULL THEN
          result := default_value + amount;
          new_document := jsonb_utils.set(existing_document, to_jsonb(result), identifiers);
        ELSIF jsonb_typeof(existing_value) != 'number' THEN
          RAISE EXCEPTION 'Cannot increment non-numeric value %', existing_value
            USING ERRCODE = 'wrong_object_type';
        ELSE
          result := existing_value::text::numeric + amount;
          new_document := jsonb_utils.set(existing_document, to_jsonb(result), identifiers);
        END IF;
        EXECUTE format(
          'UPDATE %I.%I SET json_data = $2 WHERE %s',
          schemaname,
          config_category,
          whereclause
          ) USING pkeys, new_document;
      END IF;
    ELSE
      RAISE EXCEPTION 'Cannot increment document(s)'
        USING ERRCODE = 'wrong_object_type';
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  config.toggle(
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
    LANGUAGE plpgsql
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', cog_name, cog_id);
    pkey_placeholders text[] := '{}'::text[];
    idx integer;
    num_identifiers CONSTANT integer := coalesce(array_length(identifiers, 1), 0);
    existing_document jsonb;
    existing_value jsonb;
    new_document jsonb;
    where_conditions text[] := '{}';
    whereclause text;
  BEGIN
    PERFORM config.maybe_create_table(cog_name, cog_id, config_category, pkey_len, pkey_type);
    IF num_identifiers > 0 THEN
      FOR idx IN SELECT generate_series(1, pkey_len) LOOP
        SELECT
          array_append(where_conditions, format('%I = $1[%s]', 'primary_key_'||idx, idx))
          INTO where_conditions;
      END LOOP;
      whereclause := array_to_string(where_conditions, ' AND ');
      EXECUTE format(
          'SELECT json_data FROM %I.%I WHERE %s',
          schemaname,
          config_category,
          whereclause
        ) INTO existing_document USING pkeys;
      IF existing_document IS NULL THEN
        new_document := jsonb_utils.set('{}', NOT default_value, VARIADIC identifiers);
        FOR idx IN SELECT generate_series(1, pkey_len) LOOP
          SELECT
            array_append(pkey_placeholders, format('$1[%s]::%s', idx, pkey_type))
            INTO pkey_placeholders;
        END LOOP;
        EXECUTE format(
          'INSERT INTO %I.%I VALUES(%s, $2)',
          schemaname,
          config_category,
          array_to_string(pkey_placeholders, ', ')
          ) USING pkeys, new_document;
        result := NOT default_value;
      ELSE
        existing_value := existing_document #> identifiers;
        IF existing_value IS NULL THEN
          result := NOT default_value;
          new_document := jsonb_utils.set(existing_document, to_jsonb(result), identifiers);
        ELSIF jsonb_typeof(existing_value) != 'boolean' THEN
          RAISE EXCEPTION 'Cannot increment non-boolean value %', existing_value
            USING ERRCODE = 'wrong_object_type';
        ELSE
          result := NOT existing_value::text::boolean;
          new_document := jsonb_utils.set(existing_document, to_jsonb(result), identifiers);
        END IF;
        EXECUTE format(
          'UPDATE %I.%I SET json_data = $2 WHERE %s',
          schemaname,
          config_category,
          whereclause
          ) USING pkeys, new_document;
      END IF;
    ELSE
      RAISE EXCEPTION 'Cannot increment document(s)'
        USING ERRCODE = 'wrong_object_type';
    END IF;
  END;
$$;


/*
 * Like `jsonb_set` but will insert new objects where one is missing along the path.
 */

CREATE OR REPLACE FUNCTION
  jsonb_utils.set(target jsonb, new_value jsonb, VARIADIC identifiers text[])
    RETURNS jsonb
    LANGUAGE plpgsql
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
  jsonb_utils.generate_rows_from_object(object jsonb, num_missing_pkeys integer)
    RETURNS setof record
    LANGUAGE plpgsql
  AS $$
  DECLARE
    pair record;
    column_definition_list text[] := '{}';
    idx integer;
  BEGIN
    IF num_missing_pkeys = 1 THEN
      RETURN QUERY
        SELECT key AS key_1, value AS json_data
        FROM jsonb_each(object);
    ELSE
      FOR idx IN SELECT generate_series(2, num_missing_pkeys) LOOP
        column_definition_list := array_append(
          column_definition_list, format('%I text', 'key_'||idx::text)
        );
      END LOOP;
      FOR pair IN SELECT * FROM jsonb_each(object) LOOP
        RETURN QUERY EXECUTE format($query$
            SELECT $1 AS key_1, *
            FROM jsonb_utils.generate_rows_from_object($2, $3)
              AS f(%s, json_data jsonb)
          $query$,
          array_to_string(column_definition_list, ', ')
          ) USING pair.key, pair.value, num_missing_pkeys - 1;
      END LOOP;
    END IF;
    RETURN;
  END;
$$;


/*
 * Like `jsonb_object_agg` but aggregates more than two columns into a
 * single JSONB object.
 *
 * If possible, use `jsonb_object_agg` instead for performance reasons.
 */

DROP AGGREGATE IF EXISTS jsonb_utils.agg_many(json_data jsonb, VARIADIC primary_keys text[]);
CREATE AGGREGATE jsonb_utils.agg_many(json_data jsonb, VARIADIC primary_keys text[]) (
  sfunc = jsonb_utils.set,
  stype = jsonb,
  initcond = '{}'
);


/*
 * Table to keep track of other cogs' schemas.
 */
CREATE TABLE IF NOT EXISTS config.red_cogs (
  cog_name text,
  cog_id text,
  schemaname text NOT NULL,
  PRIMARY KEY (cog_name, cog_id)
);


/*
 * Trigger for removing cog's entry from `config.red_cogs` table when schema is dropped.
 */

CREATE OR REPLACE FUNCTION
  config.drop_schema_trigger_function()
    RETURNS event_trigger
    LANGUAGE plpgsql
  AS $$
  DECLARE
    obj record;
  BEGIN
    FOR obj IN SELECT * FROM pg_event_trigger_dropped_objects() LOOP
      DELETE FROM config.red_cogs AS r WHERE r.schemaname = obj.object_name;
    END LOOP;
  END;
$$;
DROP EVENT TRIGGER IF EXISTS red_drop_schema_trigger;
CREATE EVENT TRIGGER red_drop_schema_trigger
  ON SQL_DROP
  WHEN TAG IN ('DROP SCHEMA')
  EXECUTE PROCEDURE config.drop_schema_trigger_function()
;
