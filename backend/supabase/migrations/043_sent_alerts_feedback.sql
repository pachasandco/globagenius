-- Migration 043: feedback column on sent_alerts — chantier feedback (2026-05-17)
--
-- Three values: 'good' (👍), 'bad' (👎), 'too_late' (⏱️). NULL = no
-- feedback yet. The callback handler in bot_handler.py writes here
-- on each click. Editable: a user can change their mind (last click
-- wins), so the column UPDATEs, never INSERTs.
--
-- Linked to message_id (chantier 1): all N rows of one Telegram
-- message share the feedback. The UPDATE targets every row with the
-- same message_id so the per-message analytics line up.

ALTER TABLE sent_alerts
  ADD COLUMN IF NOT EXISTS feedback varchar(16),
  ADD COLUMN IF NOT EXISTS feedback_at timestamptz;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'sent_alerts_feedback_check'
  ) THEN
    ALTER TABLE sent_alerts
      ADD CONSTRAINT sent_alerts_feedback_check
      CHECK (feedback IS NULL OR feedback IN ('good', 'bad', 'too_late'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_sent_alerts_feedback
  ON sent_alerts(feedback) WHERE feedback IS NOT NULL;
