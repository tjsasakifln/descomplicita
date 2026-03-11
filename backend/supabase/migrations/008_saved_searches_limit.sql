-- Migration 008: Limit saved_searches per user (TD-DB-012)
-- Prevents unbounded growth. Frontend already caps at 10,
-- this enforces the limit at DB level as defense-in-depth.

CREATE OR REPLACE FUNCTION check_saved_searches_limit()
RETURNS TRIGGER AS $$
DECLARE
  search_count INTEGER;
  max_searches CONSTANT INTEGER := 10;
BEGIN
  SELECT COUNT(*) INTO search_count
  FROM public.saved_searches
  WHERE user_id = NEW.user_id;

  IF search_count >= max_searches THEN
    RAISE EXCEPTION 'User has reached the maximum of % saved searches', max_searches;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_saved_searches_limit
  BEFORE INSERT ON public.saved_searches
  FOR EACH ROW
  EXECUTE FUNCTION check_saved_searches_limit();
