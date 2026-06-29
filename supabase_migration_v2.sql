-- Migration v2: Add categories, budgets, and scheduled_payments tables
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- Safe to run multiple times — uses IF NOT EXISTS

-- 1. Custom categories per user
CREATE TABLE IF NOT EXISTS categories (
  id               uuid primary key default gen_random_uuid(),
  telegram_user_id bigint not null,
  name             text not null,
  emoji            text default '🏷️',
  type             text not null default 'expense',  -- 'expense' | 'income' | 'both'
  color            text,
  created_at       timestamptz default now()
);
CREATE INDEX IF NOT EXISTS idx_categories_user ON categories(telegram_user_id);

-- 2. Monthly budget limits per category per user
CREATE TABLE IF NOT EXISTS budgets (
  id               uuid primary key default gen_random_uuid(),
  telegram_user_id bigint not null,
  month            int not null,          -- 1-12
  year             int not null,
  category         text not null,
  limit_amount     numeric not null default 0,
  created_at       timestamptz default now(),
  unique(telegram_user_id, month, year, category)
);
CREATE INDEX IF NOT EXISTS idx_budgets_user ON budgets(telegram_user_id);

-- 3. Scheduled / recurring payments
CREATE TABLE IF NOT EXISTS scheduled_payments (
  id               uuid primary key default gen_random_uuid(),
  telegram_user_id bigint not null,
  name             text not null,
  amount           numeric not null,
  category         text default '',
  icon             text,
  is_recurring     boolean default true,
  recurrence_type  text default 'monthly',   -- 'monthly' | 'weekly' | 'yearly' | 'once'
  due_day          int,                        -- day of month 1-31 for recurring
  due_date         date,                       -- exact date for one-time payments
  is_paid          boolean default false,
  paid_at          timestamptz,
  paid_months      text[] default '{}',        -- ["2024-06","2024-07"] for per-month tracking
  created_at       timestamptz default now()
);
CREATE INDEX IF NOT EXISTS idx_scheduled_payments_user ON scheduled_payments(telegram_user_id);
