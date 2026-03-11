-- Migration 007: Add UNIQUE constraint on users.email (TD-DB-003)
-- Defense in depth: auth.users already enforces uniqueness,
-- but this protects against edge cases in direct DB access.

ALTER TABLE public.users
  ADD CONSTRAINT users_email_unique UNIQUE (email);
