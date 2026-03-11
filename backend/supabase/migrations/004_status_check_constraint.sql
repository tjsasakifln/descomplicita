-- Migration 004: Add CHECK constraint on search_history.status
-- Story 0.2, Task 5 (TD-DB-001 / TD-DB-017)
--
-- Enforces that only valid status values can be stored. The 'cancelled'
-- status is new -- previously, user-initiated cancellations were recorded
-- as 'failed'. This migration formalises the allowed set.
--
-- Note: existing rows that were cancelled but stored as 'failed' cannot
-- be reliably distinguished (no reason/message column), so no retroactive
-- fixup is attempted. Going forward, cancellations use 'cancelled'.

ALTER TABLE search_history
  ADD CONSTRAINT search_history_status_check
  CHECK (status IN ('queued', 'completed', 'failed', 'cancelled'));
