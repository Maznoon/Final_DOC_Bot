# Urban Emergency Preparedness Kit Telegram Bot

A production-ready Telegram e-commerce bot built with Python, aiogram, and PostgreSQL.

## Features
- Fully Persian (Farsi) interface with RTL support.
- Persian digit conversion for all user-facing numbers.
- Step-by-step Order Wizard (FSM).
- Card-to-Card payment flow with receipt verification.
- Mock Payment Gateway integration.
- Admin Panel for order and product management.
- Support system with admin messaging.
- Dockerized setup.

## Setup
1. Copy `.env.example` to `.env` and fill in your values.
2. Run `docker-compose up -d --build`.
3. Seed the database: `docker-compose exec bot python -m src.db.seed`.

For detailed instructions in Persian, see [README_FA.md](./README_FA.md).
