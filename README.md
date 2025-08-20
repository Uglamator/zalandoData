# zalandoData

Zalando Product Analytics (Streamlit)

## Deploy to Render with PostgreSQL

1. Provision a PostgreSQL instance on Render.
2. Set environment variables on your Streamlit service:
   - `DATABASE_URL`: Render postgres URL (Render usually exposes this as `DATABASE_URL`).
   - `DB_TABLE`: products (or your chosen table name)
   - Optional fallback: leave unset to use the CSV at build time.
3. Requirements now include SQLAlchemy and psycopg2-binary for DB access.

## Seeding the database
If you are migrating from the CSV, create a table and load the CSV:

- Schema suggestion (flexible):
  - Use a wide table with columns matching the CSV headers.
  - Create indexes on `brand_clean`, `specific_category`, and `product_url`/`sku` for speed.

You can seed via psql:

```sql
CREATE TABLE IF NOT EXISTS products (
  sku text,
  brand_clean text,
  product_name_clean text,
  name_clean text,
  best_name text,
  category_clean text,
  specific_category text,
  color_clean text,
  initial_price numeric,
  final_price numeric,
  discount_pct numeric,
  pack_size integer,
  price_per_item numeric,
  product_url text,
  country_code text,
  sizes text,
  in_stock integer,
  total integer,
  snapshot_at timestamp with time zone,
  main_image text
);
```

Then copy data (from your local or a public CSV):

```sql
\copy products FROM 'cleaned_zalando_data.csv' CSV HEADER;
```

Alternative: use any ETL tool or a small Python script to load the CSV using SQLAlchemy.

## App behavior
- The app first tries to read from the database (`DATABASE_URL`, table `DB_TABLE`).
- If no DB is configured or the query returns empty, it falls back to the hosted CSV.
- A small widget in the Dashboard shows DB connection status and row count.

## Local development
```
pip install -r requirements.txt
streamlit run app.py
```

Set `DATABASE_URL` in your environment to exercise DB mode locally.
