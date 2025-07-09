# Telegram Clinic Appointment Bot

## Description

This Telegram bot facilitates booking and managing clinic appointments with doctors. Users can view registered doctors, check their availability, select appointment dates, view their own appointments, and manage them. Doctors have a separate menu for potential future management tasks. The bot also includes a feature for users to view doctor reviews.

## Features

*   **User Registration & Personalization:**
    *   Prompts new users for their name for a personalized experience.
*   **View Doctors:**
    *   Lists all registered doctors with their names and specialties.
*   **Doctor Availability:**
    *   Shows available dates for a selected doctor within the next 7 days.
*   **Appointment Date Selection:**
    *   Allows users to select a preferred date for their appointment (time selection and final booking are currently placeholders).
*   **My Appointments:**
    *   Displays a list of the user's scheduled appointments with details (doctor, date, time, status).
*   **Doctor Reviews:**
    *   Users can select a doctor and view reviews submitted by other patients.
*   **Cancel Appointment:**
    *   Users can view their active (scheduled) appointments and cancel them.
    *   Cancellation updates the appointment status and makes the doctor's schedule slot available again.
*   **Doctor Menu (Basic):**
    *   A placeholder menu for users registered as doctors, intended for future doctor-specific functionalities (e.g., managing schedule, viewing their appointments).
*   **Stateful Conversations:**
    *   Manages conversation flow using Telegram Bot API's `ConversationHandler`.
*   **Database Integration:**
    *   Uses SQLAlchemy for ORM and database interactions (defaulting to SQLite).
*   **Data Seeding:**
    *   Includes a script (`seed_db.py`) to populate the database with sample data for testing and demonstration.

## Setup and Installation

### Prerequisites

*   Python 3.8+

### Steps

1.  **Clone the Repository (Example)**
    ```bash
    git clone <your-repository-url>
    cd telegram-clinic-bot # Or your project's root folder
    ```

2.  **Create and Activate a Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**
    Navigate to the `telegram_bot_project` directory (if your `requirements.txt` is there, adjust path if it's in the root):
    ```bash
    cd telegram_bot_project
    pip install -r requirements.txt
    ```
    If `requirements.txt` is in the project root, just run `pip install -r requirements.txt` from the root.

4.  **Configuration (`telegram_bot_project/config.py`)**
    You need to create/update `telegram_bot_project/config.py` with your Telegram Bot Token and Database URI.
    ```python
    # Telegram Bot Token from BotFather
    TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

    # Database connection string
    # Default SQLite:
    DATABASE_URI = "sqlite:///./clinic_bot.db"
    # For PostgreSQL: "postgresql://user:password@host:port/database"
    # For MySQL: "mysql+mysqlconnector://user:password@host:port/database"
    ```
    **Important:** For production, use environment variables for sensitive data like `TELEGRAM_BOT_TOKEN` and `DATABASE_URI`.

## Database Setup

1.  **Initialize Database Tables:**
    The database tables are automatically created (if they don't exist) when the bot is run for the first time, due to `init_db()` being called in `bot.py`.

2.  **Seed Database with Sample Data (Optional but Recommended for Testing):**
    To populate the database with sample doctors, schedules, users, appointments, and reviews, run the `seed_db.py` script.
    *   Ensure your `DATABASE_URI` in `config.py` is correctly set.
    *   If your `seed_db.py` is inside `telegram_bot_project` and you are in the parent directory:
        ```bash
        python -m telegram_bot_project.seed_db
        ```
    *   If you are inside the `telegram_bot_project` directory:
        ```bash
        python seed_db.py
        ```

## Running the Bot

Navigate to the directory containing the `telegram_bot_project` package (i.e., the parent directory of `telegram_bot_project`) and run:

```bash
python -m telegram_bot_project.bot
```

Alternatively, if you are inside the `telegram_bot_project` directory, you might be able to run:
```bash
python bot.py
```
(This depends on your Python path configuration for relative imports.)

The bot will start polling for updates. You can interact with it by sending commands to your bot on Telegram (starting with `/start`).

## Project Structure

```
telegram-clinic-bot/ (example root folder)
├── telegram_bot_project/
│   ├── bot.py              # Main bot logic, command handlers, conversation states
│   ├── models.py           # SQLAlchemy database models
│   ├── database.py         # Database engine setup, session management, init_db
│   ├── config.py           # Configuration (Bot Token, Database URI)
│   ├── requirements.txt    # Python dependencies
│   ├── seed_db.py          # Script to populate DB with sample data
│   └── README.md           # This file
└── venv/                   # Virtual environment (if created)
```

## Error Handling

The bot includes basic error handling:
*   A global error handler (`error_handler` in `bot.py`) logs unexpected errors.
*   Specific `try-except` blocks are implemented in some handlers (e.g., user name input, some callback queries) to manage common issues like database errors or invalid input.
*   Further enhancements to error handling in all callback functions were conceptually outlined and are recommended for manual implementation for a more robust system.

## Potential Future Enhancements

*   Full appointment booking flow (time slot selection, confirmation).
*   Doctor-specific functionalities in the "Doctor Menu" (e.g., managing availability, viewing their appointments).
*   Admin panel for managing doctors, users, and system settings.
*   Notifications/reminders for appointments.
*   More detailed user profiles.
*   Ability for users to write reviews.
*   Internationalization/Localization.

---

This README provides a basic guide to understanding, setting up, and running the Telegram Clinic Appointment Bot.
```
