import logging
from enum import Enum

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Assuming config.py, models.py, database.py are in the same directory or accessible in PYTHONPATH
try:
    from telegram_bot_project.config import TELEGRAM_BOT_TOKEN, DATABASE_URI
    from telegram_bot_project.database import db_session, init_db
    from telegram_bot_project.models import User, Doctor, DoctorSchedule, Appointment, Review, UserRole
except ImportError:
    # This block is for when running bot.py directly from within telegram_bot_project folder
    from config import TELEGRAM_BOT_TOKEN, DATABASE_URI
    from database import db_session, init_db
    from models import User, Doctor, DoctorSchedule, Appointment, Review, UserRole


# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Conversation States ---
class States(Enum):
    MAIN_MENU = 0
    SELECTING_DOCTOR = 1
    SELECTING_DATE = 2
    VIEWING_APPOINTMENTS = 3
    VIEWING_REVIEWS_DOCTOR_LIST = 4 # Step 1: Show doctors to pick for reviews
    VIEWING_REVIEWS_FOR_DOCTOR = 5  # Step 2: Show reviews for a selected doctor
    CANCELLING_APPOINTMENT_LIST = 6 # Step 1: Show appointments to cancel
    # CANCELLING_APPOINTMENT_CONFIRM = 7 # Step 2: Confirm cancellation (if needed)
    CANCELLING_APPOINTMENT_CONFIRM = 7
    DOCTOR_MENU = 8
    AWAITING_NAME = 9 # New state for collecting user's name


# --- Helper Functions ---
def format_appointment_for_display(appointment: Appointment, include_doctor_specialty=True) -> str:
    """Formats a single appointment for display."""
    if not appointment.doctor or not appointment.doctor.user_account:
        doc_name = "N/A"
    else:
        doc_name_parts = []
        if appointment.doctor.user_account.first_name:
            doc_name_parts.append(appointment.doctor.user_account.first_name)
        if appointment.doctor.user_account.last_name:
            doc_name_parts.append(appointment.doctor.user_account.last_name)
        doc_name = " ".join(doc_name_parts) if doc_name_parts else f"ID: {appointment.doctor_id}"

    date_str = appointment.appointment_time.strftime("%a, %b %d, %Y")
    time_str = appointment.appointment_time.strftime("%I:%M %p") # e.g., 03:00 PM
    status_str = appointment.status.value.replace("_", " ").title()

    return f"닥터. {doc_name} ({appointment.doctor.specialty if appointment.doctor else 'N/A'})\n" \
           f"날짜: {date_str} at {time_str}\n" \
           f"상태: {status_str}"

def format_review_for_display(review: Review) -> str:
    """Formats a single review for display."""
    user_name = "Anonymous"
    if review.user:
        user_name_parts = []
        if review.user.first_name: user_name_parts.append(review.user.first_name)
        # Optionally add last initial or keep it simple
        # if review.user.last_name: user_name_parts.append(review.user.last_name[0] + ".")
        if user_name_parts: user_name = " ".join(user_name_parts)

    rating_stars = "⭐" * review.rating + "☆" * (5 - review.rating)
    comment_str = f"\nComment: {review.comment}" if review.comment else ""

    return f"Review by {user_name} ({review.created_at.strftime('%Y-%m-%d')})\n" \
           f"Rating: {rating_stars}{comment_str}"


def get_user(telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> User:
    """Gets or creates a user in the database."""
    user = db_session.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        db_session.add(user)
        db_session.commit()
        logger.info(f"New user created: {telegram_id} - {username}")
    elif user.username != username or user.first_name != first_name or user.last_name != last_name:
        # Update user info if it has changed
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        db_session.commit()
        logger.info(f"User info updated: {telegram_id}")
    return user

def is_doctor(user_id: int) -> bool:
    """Checks if the user (by internal DB ID, not Telegram ID) is a registered doctor."""
    user = db_session.query(User).filter(User.id == user_id).first()
    if user and user.role == UserRole.DOCTOR:
        # Also check if there's a corresponding entry in the Doctors table
        doctor_profile = db_session.query(Doctor).filter(Doctor.user_id == user.id).first()
        return doctor_profile is not None
    return False

def is_telegram_id_doctor(telegram_id: int) -> bool:
    """Checks if the user (by Telegram ID) is a registered doctor."""
    user = db_session.query(User).filter(User.telegram_id == telegram_id).first()
    if user and user.role == UserRole.DOCTOR:
        doctor_profile = db_session.query(Doctor).filter(Doctor.user_id == user.id).first()
        return doctor_profile is not None
    return False


# --- Main Menu Keyboard ---
def main_menu_keyboard(telegram_user_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("👨‍⚕️ View Doctors", callback_data="view_doctors")],
        [InlineKeyboardButton("🗓️ My Appointments", callback_data="my_appointments")],
        [InlineKeyboardButton("🌟 Doctor Reviews", callback_data="doctor_reviews")],
        [InlineKeyboardButton("❌ Cancel Appointment", callback_data="cancel_appointment_list")],
    ]
    if is_telegram_id_doctor(telegram_user_id):
        keyboard.append([InlineKeyboardButton("🩺 Doctor Menu 🩺", callback_data="doctor_menu")])
    return InlineKeyboardMarkup(keyboard)

import datetime # Required for date calculations

# --- Placeholder for other keyboards ---
def doctors_list_keyboard(doctors: list[Doctor]) -> InlineKeyboardMarkup:
    keyboard = []
    for doc in doctors:
        # Assuming doc.user_account links back to a User model with first_name
        # and potentially last_name
        doc_name_parts = []
        if doc.user_account:
            if doc.user_account.first_name:
                doc_name_parts.append(doc.user_account.first_name)
            if doc.user_account.last_name:
                doc_name_parts.append(doc.user_account.last_name)

        doc_display_name = " ".join(doc_name_parts) if doc_name_parts else f"Doctor ID: {doc.id}"
        keyboard.append([InlineKeyboardButton(f"Dr. {doc_display_name} - {doc.specialty}", callback_data=f"select_doctor_{doc.id}")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def doctors_list_for_reviews_keyboard(doctors: list[Doctor]) -> InlineKeyboardMarkup:
    keyboard = []
    for doc in doctors:
        doc_name_parts = []
        if doc.user_account:
            if doc.user_account.first_name: doc_name_parts.append(doc.user_account.first_name)
            if doc.user_account.last_name: doc_name_parts.append(doc.user_account.last_name)
        doc_display_name = " ".join(doc_name_parts) if doc_name_parts else f"Doctor ID: {doc.id}"
        keyboard.append([InlineKeyboardButton(f"Dr. {doc_display_name} - {doc.specialty}", callback_data=f"review_doctor_{doc.id}")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def user_appointments_for_cancellation_keyboard(appointments: list[Appointment]) -> InlineKeyboardMarkup:
    keyboard = []
    for appt in appointments:
        # Only list cancellable appointments (e.g., status is SCHEDULED)
        if appt.status == AppointmentStatus.SCHEDULED:
            # Format a brief description for the button
            doc_name = "N/A"
            if appt.doctor and appt.doctor.user_account and appt.doctor.user_account.first_name:
                doc_name = f"Dr. {appt.doctor.user_account.first_name}"
            date_str = appt.appointment_time.strftime("%a, %b %d - %I:%M %p")
            button_text = f"{doc_name} on {date_str}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"confirm_cancel_{appt.id}")])

    if not keyboard: # No cancellable appointments found to list
        # This case should ideally be handled before calling this keyboard function,
        # by checking if there are any cancellable appointments.
        # If called with an empty list of suitable appointments, it will show just the back button.
        pass

    keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def format_date_for_display(date_obj: datetime.date) -> str:
    """Formats a date object as 'Day, Mon DD' (e.g., 'Mon, Jul 29')."""
    return date_obj.strftime("%a, %b %d")

def available_dates_keyboard(doctor_id: int, available_dates: list[datetime.date]) -> InlineKeyboardMarkup:
    keyboard = []
    # Display dates nicely, e.g., "Mon, Jul 29"
    for date_obj in available_dates:
        display_text = format_date_for_display(date_obj)
        callback_data_date = date_obj.strftime("%Y-%m-%d") # Use ISO format for callback data
        keyboard.append([InlineKeyboardButton(display_text, callback_data=f"select_date_{doctor_id}_{callback_data_date}")])

    keyboard.append([InlineKeyboardButton("⬅️ Back to Doctors", callback_data="view_doctors")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


# --- Bot Command Handlers (will be expanded in next steps) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a welcome message and displays the main menu."""
    telegram_user = update.effective_user
    # Get or create user in DB
    db_user = get_user(telegram_id=telegram_user.id, username=telegram_user.username, first_name=telegram_user.first_name, last_name=telegram_user.last_name)

    context.user_data['db_user_id'] = db_user.id # Store internal DB user ID
    logger.info(f"User {telegram_user.id} (DB ID: {db_user.id}) initiated /start command.")

    # Check if user's name is already known (e.g., in db_user.first_name)
    # We use db_user.first_name as the primary field for the collected name.
    # Telegram's telegram_user.first_name can be a default if nothing is in DB.

    user_display_name = db_user.first_name or telegram_user.first_name

    if not db_user.first_name: # If we don't have a name stored specifically by our bot
        logger.info(f"User DB_ID {db_user.id} has no stored name. Requesting name. State: AWAITING_NAME")
        if update.message:
            await update.message.reply_text("Welcome! To personalize your experience, please tell me your name.")
        elif update.callback_query: # Should not typically happen for initial start, but good for robustness
             await update.callback_query.edit_message_text("Welcome! To personalize your experience, please tell me your name.")
        return States.AWAITING_NAME
    else:
        logger.info(f"User DB_ID {db_user.id} (Name: {user_display_name}) already has a name. Proceeding to main menu. State: MAIN_MENU")
        welcome_text = f"Welcome back, {user_display_name}!\nHow can I help you today?"
        if update.message:
            await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard(telegram_user.id))
        elif update.callback_query: # If start is called from a callback (e.g. fallback)
            await update.callback_query.edit_message_text(welcome_text, reply_markup=main_menu_keyboard(telegram_user.id))
        return States.MAIN_MENU

async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's name input after being prompted."""
    user_input_name = update.message.text.strip()
    telegram_user = update.effective_user

    db_user = get_user(telegram_id=telegram_user.id, username=telegram_user.username, first_name=telegram_user.first_name, last_name=telegram_user.last_name)

    if not user_input_name or len(user_input_name) < 2: # Basic validation
        await update.message.reply_text("That seems a bit short for a name. Please try again:")
        return States.AWAITING_NAME # Stay in the same state

    # Update the user's first_name in the database with the provided name
    db_user.first_name = user_input_name
    # context.user_data['db_user_first_name'] = user_input_name # Not strictly needed if we re-fetch or use db_user
    try:
        db_session.commit()
        logger.info(f"User DB_ID {db_user.id} provided name: {user_input_name}. Updated in DB.")
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error saving name for user {db_user.id}: {e}")
        await update.message.reply_text("Sorry, there was an error saving your name. Please try /start again later.")
        return ConversationHandler.END # End conversation on error

    welcome_text = f"Thanks, {user_input_name}!\nHow can I help you today?"
    await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard(telegram_user.id))
    return States.MAIN_MENU


async def view_doctors_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the 'View Doctors' button click."""
    query = update.callback_query
    await query.answer() # Acknowledge callback
    try:
        doctors = db_session.query(Doctor).join(User, Doctor.user_id == User.id).all() # Join with User to access names
        logger.info(f"Found {len(doctors)} doctors in the database.")
        if not doctors:
            await query.edit_message_text(
                text="Currently, there are no doctors registered. Please check back later.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")]])
            )
        else:
            await query.edit_message_text(
                text="Please select a doctor:",
                reply_markup=doctors_list_keyboard(doctors)
            )
        logger.info(f"User {update.effective_user.id} viewed doctors list. State: SELECTING_DOCTOR")
        return States.SELECTING_DOCTOR
    except Exception as e:
        logger.error(f"Error in view_doctors_callback: {e}")
        if query.message: # Ensure there's a message to edit
            await query.edit_message_text("Sorry, an error occurred while fetching doctors. Please try again later.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")]]))
        return States.MAIN_MENU


async def select_doctor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the selection of a doctor and shows available dates."""
    query = update.callback_query
    await query.answer()

    try:
        doctor_id_str = query.data.split("_")[-1]
        if not doctor_id_str.isdigit():
            raise ValueError("Doctor ID is not a number")
        doctor_id = int(doctor_id_str)
        context.user_data['selected_doctor_id'] = doctor_id

        doctor = db_session.query(Doctor).filter(Doctor.id == doctor_id).first()
        if not doctor:
            all_doctors = db_session.query(Doctor).join(User, Doctor.user_id == User.id).all()
            await query.edit_message_text(
                text="Error: Doctor not found. Please select from the updated list:",
                reply_markup=doctors_list_keyboard(all_doctors)
            )
            return States.SELECTING_DOCTOR

        today = datetime.date.today()
        end_date = today + datetime.timedelta(days=7)
        from sqlalchemy import func as sql_func

        available_schedule_dates = db_session.query(
                sql_func.date(DoctorSchedule.available_date)
            ).filter(
                DoctorSchedule.doctor_id == doctor_id,
                DoctorSchedule.available_date >= datetime.datetime.combine(today, datetime.time.min),
                DoctorSchedule.available_date < datetime.datetime.combine(end_date, datetime.time.min),
                DoctorSchedule.is_booked == 0
            ).distinct().order_by(sql_func.date(DoctorSchedule.available_date)).all()

        available_dates = [result[0] for result in available_schedule_dates]

        doc_name_parts = []
        if doctor.user_account:
            if doctor.user_account.first_name:
                doc_name_parts.append(doctor.user_account.first_name)
            if doctor.user_account.last_name:
                doc_name_parts.append(doctor.user_account.last_name)
        doc_display_name = " ".join(doc_name_parts) if doc_name_parts else f"Doctor ID: {doctor.id}"
        specialty = doctor.specialty or 'N/A'

        if not available_dates:
            await query.edit_message_text(
                text=f"Dr. {doc_display_name} ({specialty}) has no available dates in the next 7 days.",
                reply_markup=available_dates_keyboard(doctor_id, [])
            )
        else:
            await query.edit_message_text(
                text=f"Available dates for Dr. {doc_display_name} ({specialty}):",
                reply_markup=available_dates_keyboard(doctor_id, available_dates)
            )

        logger.info(f"User {update.effective_user.id} selected doctor {doctor_id}. Showing dates. State: SELECTING_DATE")
        return States.SELECTING_DATE
    except ValueError as ve:
        logger.error(f"Invalid doctor_id in callback data: {query.data} - {ve}")
        all_doctors = db_session.query(Doctor).join(User, Doctor.user_id == User.id).all()
        if query.message:
            await query.edit_message_text("Error: Invalid doctor selection. Please try again.",
                                      reply_markup=doctors_list_keyboard(all_doctors))
        return States.SELECTING_DOCTOR
    except Exception as e:
        logger.error(f"Error in select_doctor_callback: {e}")
        all_doctors = db_session.query(Doctor).join(User, Doctor.user_id == User.id).all()
        if query.message:
            await query.edit_message_text("Sorry, an error occurred. Please try selecting a doctor again.",
                                      reply_markup=doctors_list_keyboard(all_doctors))
        return States.SELECTING_DOCTOR


async def select_date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the selection of an appointment date."""
    query = update.callback_query
    await query.answer()

    try:
        parts = query.data.split("_")
        if len(parts) < 3: # select_date_DOCTORID_YYYY-MM-DD
            raise ValueError("Callback data format incorrect for date selection.")

        doctor_id_str = parts[-2]
        if not doctor_id_str.isdigit():
            raise ValueError("Doctor ID part of callback data is not a number.")
        doctor_id = int(doctor_id_str)

        selected_date_str = parts[-1]
        context.user_data['selected_date_str'] = selected_date_str

        doctor = db_session.query(Doctor).filter(Doctor.id == doctor_id).first()
        doc_display_name = "Unknown Doctor"
        if doctor and doctor.user_account:
            doc_name_parts = []
            if doctor.user_account.first_name: doc_name_parts.append(doctor.user_account.first_name)
            if doctor.user_account.last_name: doc_name_parts.append(doctor.user_account.last_name)
            doc_display_name = " ".join(doc_name_parts) if doc_name_parts else f"Doctor ID: {doctor.id}"
        elif doctor:
             doc_display_name = f"Doctor ID: {doctor.id}"

        selected_date_obj = datetime.datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        formatted_date_display = format_date_for_display(selected_date_obj)

        confirmation_text = (
            f"You've selected {formatted_date_display} with Dr. {doc_display_name}.\n\n"
            "Next steps would be to select a time slot and confirm booking.\n"
            "(Time slot selection is not yet implemented in this version.)"
        )

        keyboard = [
            [InlineKeyboardButton("⬅️ Change Date (Show Dr. Dates)", callback_data=f"select_doctor_{doctor_id}")],
            [InlineKeyboardButton("⬅️ Change Doctor", callback_data="view_doctors")],
            [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if query.message:
            await query.edit_message_text(text=confirmation_text, reply_markup=reply_markup)

        logger.info(f"User {update.effective_user.id} selected date {selected_date_str} for doctor {doctor_id}.")
        return States.SELECTING_DATE
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing callback data in select_date_callback: {query.data} - {e}")
        if query.message:
            await query.edit_message_text("Sorry, there was an error processing your date selection. Please try again.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]]))
        return States.MAIN_MENU # Or specific recovery state
    except Exception as e:
        logger.error(f"Error in select_date_callback: {e}")
        if query.message:
            await query.edit_message_text("Sorry, an unexpected error occurred. Please try again.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]]))
        return States.MAIN_MENU

async def my_appointments_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the 'My Appointments' button click."""
    query = update.callback_query
    await query.answer()

    try:
        db_user_id = context.user_data.get('db_user_id')
        if not db_user_id:
            logger.warning("db_user_id not found in context for my_appointments_callback.")
            if query.message:
                await query.edit_message_text(
                    text="Could not identify you. Please /start the bot again.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")]])
                )
            return States.MAIN_MENU

        user_appointments = db_session.query(Appointment).filter(Appointment.user_id == db_user_id)\
            .order_by(Appointment.appointment_time.asc()).all()

        if not user_appointments:
            text = "You have no scheduled appointments."
        else:
            text = "Here are your appointments:\n\n"
            for appt in user_appointments:
                text += format_appointment_for_display(appt) + "\n\n"
            text = text.strip()

        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if query.message:
            await query.edit_message_text(text=text, reply_markup=reply_markup)

        logger.info(f"User DB_ID {db_user_id} viewed their appointments. State: VIEWING_APPOINTMENTS")
        return States.VIEWING_APPOINTMENTS
    except Exception as e:
        logger.error(f"Error in my_appointments_callback for user_id {context.user_data.get('db_user_id')}: {e}")
        if query.message:
            await query.edit_message_text("Sorry, an error occurred while fetching your appointments. Please try again later.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")]]))
        return States.MAIN_MENU


async def doctor_reviews_select_doctor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles 'Doctor Reviews' button: displays list of doctors to choose from."""
    query = update.callback_query
    await query.answer()
    try:
        doctors = db_session.query(Doctor).join(User, Doctor.user_id == User.id).all()
        if not doctors:
            if query.message:
                await query.edit_message_text(
                    text="Currently, there are no doctors registered to review.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")]])
                )
            return States.MAIN_MENU
        else:
            if query.message:
                await query.edit_message_text(
                    text="Which doctor's reviews would you like to see?",
                    reply_markup=doctors_list_for_reviews_keyboard(doctors)
                )
        logger.info(f"User {update.effective_user.id} initiated viewing doctor reviews. Showing doctor list. State: VIEWING_REVIEWS_DOCTOR_LIST")
        return States.VIEWING_REVIEWS_DOCTOR_LIST
    except Exception as e:
        logger.error(f"Error in doctor_reviews_select_doctor_callback: {e}")
        if query.message:
            await query.edit_message_text("Sorry, an error occurred. Please try again.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")]]))
        return States.MAIN_MENU

async def view_reviews_for_doctor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles selection of a doctor to view their reviews."""
    query = update.callback_query
    await query.answer()

    doctor_id = int(query.data.split("_")[-1]) # review_doctor_DOCTORID

    doctor = db_session.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor or not doctor.user_account:
        await query.edit_message_text(
            text="Error: Doctor not found. Please try again.",
            reply_markup=doctors_list_for_reviews_keyboard(db_session.query(Doctor).join(User, Doctor.user_id == User.id).all())
        )
        return States.VIEWING_REVIEWS_DOCTOR_LIST

    doc_display_name = f"Dr. {doctor.user_account.first_name} {doctor.user_account.last_name or ''}".strip()

    reviews = db_session.query(Review).filter(Review.doctor_id == doctor_id).order_by(Review.created_at.desc()).all()

    if not reviews:
        text_message = f"There are no reviews for {doc_display_name} ({doctor.specialty}) yet."
    else:
        text_message = f"Reviews for {doc_display_name} ({doctor.specialty}):\n\n"
        for review in reviews:
            text_message += format_review_for_display(review) + "\n\n"
        text_message = text_message.strip()

    keyboard = [
        [InlineKeyboardButton("⬅️ Back to Doctor List (Reviews)", callback_data="doctor_reviews")], # Re-triggers doctor_reviews_select_doctor_callback
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text=text_message, reply_markup=reply_markup)

    logger.info(f"User {update.effective_user.id} viewed reviews for doctor {doctor_id}. State: VIEWING_REVIEWS_FOR_DOCTOR")
    return States.VIEWING_REVIEWS_FOR_DOCTOR

async def list_appointments_for_cancellation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lists user's cancellable appointments."""
    query = update.callback_query
    await query.answer()

    db_user_id = context.user_data.get('db_user_id')
    if not db_user_id:
        await query.edit_message_text(
            text="Could not identify you. Please /start the bot again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")]])
        )
        return States.MAIN_MENU

    # Fetch only 'SCHEDULED' appointments for cancellation
    cancellable_appointments = db_session.query(Appointment).filter(
        Appointment.user_id == db_user_id,
        Appointment.status == AppointmentStatus.SCHEDULED
    ).order_by(Appointment.appointment_time.asc()).all()

    if not cancellable_appointments:
        await query.edit_message_text(
            text="You have no active appointments that can be cancelled.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")]])
        )
        return States.MAIN_MENU # Stay in main menu or return to it
    else:
        await query.edit_message_text(
            text="Select an appointment to cancel:",
            reply_markup=user_appointments_for_cancellation_keyboard(cancellable_appointments)
        )

    logger.info(f"User DB_ID {db_user_id} listed appointments for cancellation. State: CANCELLING_APPOINTMENT_LIST")
    return States.CANCELLING_APPOINTMENT_LIST

async def confirm_cancellation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the actual cancellation of a selected appointment."""
    query = update.callback_query
    await query.answer()

    appointment_id = int(query.data.split("_")[-1]) # confirm_cancel_APPOINTMENTID

    db_user_id = context.user_data.get('db_user_id')
    if not db_user_id: # Should ideally not happen if they got here
        await query.edit_message_text("Error identifying user. Please /start again.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")]]))
        return States.MAIN_MENU

    appointment_to_cancel = db_session.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.user_id == db_user_id # Ensure user owns this appointment
    ).first()

    if not appointment_to_cancel:
        await query.edit_message_text("Error: Appointment not found or you're not authorized to cancel it.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")]]))
        return States.CANCELLING_APPOINTMENT_LIST # Or back to main menu

    if appointment_to_cancel.status != AppointmentStatus.SCHEDULED:
        await query.edit_message_text(
            text=f"This appointment cannot be cancelled (Status: {appointment_to_cancel.status.value.replace('_', ' ').title()}).",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")]])
        )
        return States.CANCELLING_APPOINTMENT_LIST

    # Proceed with cancellation
    appointment_to_cancel.status = AppointmentStatus.CANCELLED_BY_USER
    # If this appointment was tied to a DoctorSchedule slot, mark that slot as no longer booked
    if appointment_to_cancel.schedule_id:
        schedule_slot = db_session.query(DoctorSchedule).filter(DoctorSchedule.id == appointment_to_cancel.schedule_id).first()
        if schedule_slot:
            schedule_slot.is_booked = 0 # Mark as not booked
            logger.info(f"Schedule slot {schedule_slot.id} marked as not booked due to cancellation of appointment {appointment_id}.")

    db_session.commit()

    # Format appointment details for confirmation message
    appt_details = format_appointment_for_display(appointment_to_cancel, include_doctor_specialty=False)

    await query.edit_message_text(
        text=f"Successfully cancelled your appointment:\n\n{appt_details}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗓️ View My Appointments", callback_data="my_appointments")],
            [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]
        ])
    )
    logger.info(f"User DB_ID {db_user_id} cancelled appointment {appointment_id}.")
    # After cancellation, we could go to VIEWING_APPOINTMENTS or MAIN_MENU.
    # Let's make it VIEWING_APPOINTMENTS so they see the updated list if they click the button.
    return States.VIEWING_APPOINTMENTS

async def doctor_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the 'Doctor Menu' button click."""
    query = update.callback_query
    await query.answer()

    # Verify again if the user is a doctor, though they shouldn't see the button otherwise.
    # db_user_id = context.user_data.get('db_user_id')
    # if not db_user_id or not is_doctor(db_user_id): # is_doctor needs internal ID
    # For simplicity, rely on main_menu_keyboard's check based on telegram_id
    # However, it's good practice to ensure the user is indeed a doctor if this menu provides sensitive actions.
    # For this basic version, the check in main_menu_keyboard is sufficient.

    text = (
        "🩺 **Doctor Menu** 🩺\n\n"
        "This section is for managing your schedule, appointments, and profile.\n"
        "(Full functionality coming soon!)\n\n"
        "Potential features:\n"
        "- View Your Schedule\n"
        "- Add Availability\n"
        "- View Your Appointments\n"
        "- Manage Profile"
    )

    keyboard = [
        # Add actual doctor action buttons here in the future
        # [InlineKeyboardButton("View My Schedule (Soon)", callback_data="doc_view_schedule")],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

    logger.info(f"User {update.effective_user.id} accessed Doctor Menu. State: DOCTOR_MENU")
    return States.DOCTOR_MENU


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sorry, I didn't understand that command.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logger.error(f"Update {update} caused error {context.error}")
    # Optionally, send a message to the user or a admin/developer chat
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("Sorry, something went wrong. Please try again later.")


async def start_again_from_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    telegram_user = update.effective_user
    # Ensure user exists, though they should if they reached here via a button
    db_user = get_user(telegram_id=telegram_user.id, username=telegram_user.username, first_name=telegram_user.first_name, last_name=telegram_user.last_name)
    context.user_data['db_user_id'] = db_user.id # Ensure db_user_id is in context

    await query.edit_message_text(
        text=f"Welcome back, {telegram_user.first_name}!\nHow can I help you today?",
        reply_markup=main_menu_keyboard(telegram_user.id)
    )
    return States.MAIN_MENU

def main() -> None:
    """Run the bot."""
    # Initialize DB
    init_db() # This creates tables if they don't exist

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # --- Conversation Handler Setup (to be filled in later steps) ---
    # For now, just a start command
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            States.MAIN_MENU: [
                CallbackQueryHandler(view_doctors_callback, pattern="^view_doctors$"),
                CallbackQueryHandler(my_appointments_callback, pattern="^my_appointments$"),
                CallbackQueryHandler(doctor_reviews_select_doctor_callback, pattern="^doctor_reviews$"),
                CallbackQueryHandler(list_appointments_for_cancellation_callback, pattern="^cancel_appointment_list$"),
                CallbackQueryHandler(doctor_menu_callback, pattern="^doctor_menu$"), # Handler for Doctor Menu button
                CallbackQueryHandler(start_again_from_menu, pattern="^main_menu$"),
            ],
            States.SELECTING_DOCTOR: [
                CallbackQueryHandler(select_doctor_callback, pattern="^select_doctor_\\d+$"),
                CallbackQueryHandler(start_again_from_menu, pattern="^main_menu$"),
            ],
            States.SELECTING_DATE: [
                CallbackQueryHandler(select_date_callback, pattern="^select_date_\\d+_\\d{4}-\\d{2}-\\d{2}$"),
                CallbackQueryHandler(view_doctors_callback, pattern="^view_doctors$"),
                CallbackQueryHandler(start_again_from_menu, pattern="^main_menu$"),
                CallbackQueryHandler(select_doctor_callback, pattern="^select_doctor_\\d+$"),
            ],
            States.VIEWING_APPOINTMENTS: [
                CallbackQueryHandler(my_appointments_callback, pattern="^my_appointments$"),
                CallbackQueryHandler(start_again_from_menu, pattern="^main_menu$"),
            ],
            States.VIEWING_REVIEWS_DOCTOR_LIST: [
                CallbackQueryHandler(view_reviews_for_doctor_callback, pattern="^review_doctor_\\d+$"),
                CallbackQueryHandler(start_again_from_menu, pattern="^main_menu$"),
            ],
            States.VIEWING_REVIEWS_FOR_DOCTOR: [
                CallbackQueryHandler(doctor_reviews_select_doctor_callback, pattern="^doctor_reviews$"),
                CallbackQueryHandler(start_again_from_menu, pattern="^main_menu$"),
            ],
            States.CANCELLING_APPOINTMENT_LIST: [
                CallbackQueryHandler(confirm_cancellation_callback, pattern="^confirm_cancel_\\d+$"),
                CallbackQueryHandler(start_again_from_menu, pattern="^main_menu$"),
            ],
            States.DOCTOR_MENU: [ # State for Doctor Menu
                CallbackQueryHandler(start_again_from_menu, pattern="^main_menu$"),
                # Add handlers for actual doctor actions here later
            ],
            States.AWAITING_NAME: [ # Handler for when bot is waiting for user's name
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input)
            ],
        },
        fallbacks=[CommandHandler("start", start), CallbackQueryHandler(start_again_from_menu, pattern="^main_menu$")],
        # per_user=True, per_chat=True # Default, good for most cases
    )

    application.add_handler(conv_handler) # Use the conversation handler

    # Remove standalone handlers now managed by ConversationHandler if any
    # application.add_handler(CommandHandler("start", start)) # Already an entry point
    # application.add_handler(CallbackQueryHandler(start_again_from_menu, pattern="^main_menu$")) # Now part of MAIN_MENU state


    # Handle unknown commands
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Error handler
    application.add_error_handler(error_handler)

    logger.info("Bot starting...")
    # Run the bot until the user presses Ctrl-C
    application.run_polling()

    # Clean up session on shutdown (optional, good practice)
    db_session.remove()


if __name__ == "__main__":
    main()
