-- Capture why users cancel their Premium subscription so we can spot
-- recurring product issues (pricing, signal quality, bugs…) instead of
-- guessing.  Insert happens server-side from the cancel-subscription
-- endpoint.  We deliberately keep the row even if the user later
-- deletes their account: ON DELETE SET NULL preserves the feedback
-- text without orphaning identifying data.

create table if not exists cancellation_reasons (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete set null,
  -- Short machine code: 'too_expensive', 'too_few_alerts',
  -- 'too_many_alerts', 'travelling_less', 'found_better',
  -- 'bugs', 'other', 'no_answer'.  Free-form to avoid a tight
  -- check-constraint that we'd have to keep migrating.
  reason text not null,
  feedback text,
  was_premium boolean not null default true,
  -- Stripe subscription id at the time of cancellation, useful when
  -- correlating with churn events in the Stripe dashboard.
  subscription_id text,
  created_at timestamptz not null default now()
);

create index if not exists idx_cancellation_reasons_created_at
  on cancellation_reasons (created_at desc);

create index if not exists idx_cancellation_reasons_reason
  on cancellation_reasons (reason);
