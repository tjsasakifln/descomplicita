-- Migration: 005_saved_searches_name_length.sql
-- Description: Add length constraint on saved_searches.name to prevent oversized names
-- Story: story-1.2-quick-wins-backend (TD-DB-008)

ALTER TABLE public.saved_searches
  ADD CONSTRAINT saved_searches_name_length_check
  CHECK (length(name) <= 200);
