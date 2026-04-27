-- Deduplicate existing rows: keep only the most recent qualified_item per item_id.
-- Multiple runs inserting the same raw_flight caused duplicate active rows.
DELETE FROM qualified_items
WHERE id NOT IN (
  SELECT DISTINCT ON (item_id) id
  FROM qualified_items
  ORDER BY item_id, created_at DESC
);

-- Add unique constraint so future upserts on item_id work correctly.
ALTER TABLE qualified_items
  ADD CONSTRAINT qualified_items_item_id_unique UNIQUE (item_id);
