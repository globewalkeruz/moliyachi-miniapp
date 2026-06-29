-- Migration v3: Add monthly_plans table for Next Month Planner feature
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New query)

CREATE TABLE IF NOT EXISTS monthly_plans (
  id               uuid primary key default gen_random_uuid(),
  telegram_user_id bigint not null,
  month            int not null,    -- target month (1-12)
  year             int not null,
  plan_type        text not null,   -- 'income' | 'expense'
  name             text not null,
  amount           numeric not null,
  category         text default '',
  expected_day     int,             -- day of month (1-31)
  note             text,
  created_at       timestamptz default now()
);
CREATE INDEX IF NOT EXISTS idx_monthly_plans_user ON monthly_plans(telegram_user_id);
