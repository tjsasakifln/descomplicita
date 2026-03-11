-- v3-story-2.0 Task 10: Data retention policy (DB-008)
-- Scheduled cleanup of old search history (>90 days)
-- Run via Supabase pg_cron or external cron

-- Enable pg_cron if available (Supabase Pro plan)
-- CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Cleanup function: delete search history older than 90 days
CREATE OR REPLACE FUNCTION public.cleanup_old_searches(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM public.search_history
    WHERE created_at < NOW() - (retention_days || ' days')::INTERVAL
      AND status IN ('completed', 'failed', 'cancelled');

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RAISE NOTICE 'Cleaned up % search history records older than % days', deleted_count, retention_days;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Schedule cleanup daily at 3 AM UTC (requires pg_cron extension)
-- Uncomment after enabling pg_cron in Supabase dashboard:
-- SELECT cron.schedule('cleanup-old-searches', '0 3 * * *', $$SELECT public.cleanup_old_searches(90)$$);
