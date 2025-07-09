import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Adjust the import path if your config/models are structured differently
# or if running this script from outside telegram_bot_project directory.
try:
    from config import DATABASE_URI
    from models import Base, User, Doctor, DoctorSchedule, Appointment, Review, UserRole, AppointmentStatus
    from database import db_session as Session # Use the scoped session or SessionLocal
except ImportError:
    print("Error: Could not import necessary modules. Make sure this script is run from a context where 'config.py', 'models.py', and 'database.py' are accessible.")
    print("If running from parent directory, you might need to adjust PYTHONPATH or run as 'python -m telegram_bot_project.seed_db'")
    exit(1)


def seed_database():
    """Populates the database with sample data."""

    # Clear existing data (optional, use with caution)
    # Base.metadata.drop_all(bind=Session.bind)
    # Base.metadata.create_all(bind=Session.bind)
    # print("Dropped and recreated all tables.")

    # --- Create Users ---
    user1 = User(telegram_id=111111, username="patient_alice", first_name="Alice", role=UserRole.PATIENT)
    user2 = User(telegram_id=222222, username="patient_bob", first_name="Bob", role=UserRole.PATIENT)
    user3_doc_smith = User(telegram_id=333333, username="doc_smith", first_name="John", last_name="Smith", role=UserRole.DOCTOR)
    user4_doc_jones = User(telegram_id=444444, username="doc_jones", first_name="Emily", last_name="Jones", role=UserRole.DOCTOR)
    user5_new = User(telegram_id=555555, username="new_user_sam", first_name=None) # Test name collection

    Session.add_all([user1, user2, user3_doc_smith, user4_doc_jones, user5_new])
    Session.commit() # Commit users to get their IDs

    print(f"Created Users: {user1.id}, {user2.id}, {user3_doc_smith.id}, {user4_doc_jones.id}, {user5_new.id}")

    # --- Create Doctors ---
    # Ensure users exist and have IDs before creating doctors linked to them
    doctor_smith = Doctor(user_id=user3_doc_smith.id, specialty="Cardiology", bio="Experienced cardiologist focusing on heart health.")
    doctor_jones = Doctor(user_id=user4_doc_jones.id, specialty="Pediatrics", bio="Dedicated pediatrician providing care for children of all ages.")

    Session.add_all([doctor_smith, doctor_jones])
    Session.commit() # Commit doctors to get their IDs
    print(f"Created Doctors: {doctor_smith.id} (for User {user3_doc_smith.id}), {doctor_jones.id} (for User {user4_doc_jones.id})")


    # --- Create Doctor Schedules ---
    today = datetime.date.today()
    schedules = []

    # Dr. Smith's schedule for the next 7 days
    for i in range(7):
        current_date = today + datetime.timedelta(days=i)
        # Morning slots
        schedules.append(DoctorSchedule(doctor_id=doctor_smith.id, available_date=datetime.datetime(current_date.year, current_date.month, current_date.day, 9, 0), start_time=datetime.time(9,0), end_time=datetime.time(9,30), is_booked=0))
        schedules.append(DoctorSchedule(doctor_id=doctor_smith.id, available_date=datetime.datetime(current_date.year, current_date.month, current_date.day, 9, 30), start_time=datetime.time(9,30), end_time=datetime.time(10,0), is_booked=0))
        schedules.append(DoctorSchedule(doctor_id=doctor_smith.id, available_date=datetime.datetime(current_date.year, current_date.month, current_date.day, 10, 0), start_time=datetime.time(10,0), end_time=datetime.time(10,30), is_booked=0 if i % 2 == 0 else 1)) # Book some
        # Afternoon slots (fewer)
        if i < 4 : # Only first 4 days for afternoon
             schedules.append(DoctorSchedule(doctor_id=doctor_smith.id, available_date=datetime.datetime(current_date.year, current_date.month, current_date.day, 14, 0), start_time=datetime.time(14,0), end_time=datetime.time(14,30), is_booked=0))

    # Dr. Jones's schedule for the next 7 days
    for i in range(7):
        current_date = today + datetime.timedelta(days=i)
        # Morning slots
        schedules.append(DoctorSchedule(doctor_id=doctor_jones.id, available_date=datetime.datetime(current_date.year, current_date.month, current_date.day, 11, 0), start_time=datetime.time(11,0), end_time=datetime.time(11,30), is_booked=0))
        schedules.append(DoctorSchedule(doctor_id=doctor_jones.id, available_date=datetime.datetime(current_date.year, current_date.month, current_date.day, 11, 30), start_time=datetime.time(11,30), end_time=datetime.time(12,0), is_booked=1 if i % 3 == 0 else 0)) # Book some
        # Afternoon
        if i % 2 != 0 : # Alternate days for afternoon
            schedules.append(DoctorSchedule(doctor_id=doctor_jones.id, available_date=datetime.datetime(current_date.year, current_date.month, current_date.day, 15, 0), start_time=datetime.time(15,0), end_time=datetime.time(15,30), is_booked=0))
            schedules.append(DoctorSchedule(doctor_id=doctor_jones.id, available_date=datetime.datetime(current_date.year, current_date.month, current_date.day, 15, 30), start_time=datetime.time(15,30), end_time=datetime.time(16,0), is_booked=0))

    Session.add_all(schedules)
    Session.commit()
    print(f"Created {len(schedules)} schedule entries.")

    # --- Create Appointments ---
    # Find some available slots to book for appointments
    # For User1 (Alice) with Dr. Smith
    slot_for_alice = Session.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == doctor_smith.id,
        DoctorSchedule.is_booked == 0,
        DoctorSchedule.available_date >= datetime.datetime.combine(today + datetime.timedelta(days=1), datetime.time.min) # Tomorrow onwards
    ).first()

    if slot_for_alice:
        appointment1 = Appointment(user_id=user1.id, doctor_id=doctor_smith.id, schedule_id=slot_for_alice.id, appointment_time=slot_for_alice.available_date, status=AppointmentStatus.SCHEDULED)
        slot_for_alice.is_booked = 1
        Session.add(appointment1)
        print(f"Created Appointment for Alice with Dr. Smith on {slot_for_alice.available_date.strftime('%Y-%m-%d %H:%M')}")

    # For User2 (Bob) with Dr. Jones
    slot_for_bob = Session.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == doctor_jones.id,
        DoctorSchedule.is_booked == 0,
        DoctorSchedule.available_date >= datetime.datetime.combine(today + datetime.timedelta(days=2), datetime.time.min) # Day after tomorrow
    ).first()

    if slot_for_bob:
        appointment2 = Appointment(user_id=user2.id, doctor_id=doctor_jones.id, schedule_id=slot_for_bob.id, appointment_time=slot_for_bob.available_date, status=AppointmentStatus.SCHEDULED)
        slot_for_bob.is_booked = 1
        Session.add(appointment2)
        print(f"Created Appointment for Bob with Dr. Jones on {slot_for_bob.available_date.strftime('%Y-%m-%d %H:%M')}")

    # A completed appointment for User1
    past_slot_for_alice = Session.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == doctor_jones.id,
        DoctorSchedule.is_booked == 0, # Assuming we find an unbooked past slot to simulate this
        DoctorSchedule.available_date < datetime.datetime.combine(today, datetime.time.min)
    ).order_by(DoctorSchedule.available_date.desc()).first() # Find a past slot

    # If no actual past unbooked slot, create one for the sake of example (not ideal but for seeding)
    if not past_slot_for_alice:
         past_slot_for_alice = DoctorSchedule(doctor_id=doctor_jones.id, available_date=datetime.datetime.combine(today - datetime.timedelta(days=5), datetime.time(10,0)), start_time=datetime.time(10,0), end_time=datetime.time(10,30), is_booked=1)
         Session.add(past_slot_for_alice)
         Session.commit() # Commit to get ID
         print("Created a dummy past schedule slot for completed appointment example.")


    appointment3_completed = Appointment(user_id=user1.id, doctor_id=doctor_jones.id, schedule_id=past_slot_for_alice.id, appointment_time=past_slot_for_alice.available_date, status=AppointmentStatus.COMPLETED)
    Session.add(appointment3_completed)
    print(f"Created a completed Appointment for Alice with Dr. Jones on {past_slot_for_alice.available_date.strftime('%Y-%m-%d %H:%M')}")

    Session.commit()

    # --- Create Reviews ---
    review1 = Review(user_id=user1.id, doctor_id=doctor_jones.id, rating=5, comment="Dr. Jones was fantastic with my child! Very caring and thorough.")
    review2 = Review(user_id=user2.id, doctor_id=doctor_smith.id, rating=4, comment="Dr. Smith is knowledgeable, but the wait time was a bit long.")
    review3 = Review(user_id=user1.id, doctor_id=doctor_smith.id, rating=5, comment="Excellent consultation with Dr. Smith. Highly recommend.")
    # User 2 reviews Dr Jones
    review4 = Review(user_id=user2.id, doctor_id=doctor_jones.id, rating=3, comment="Okay, but felt a bit rushed.")


    Session.add_all([review1, review2, review3, review4])
    Session.commit()
    print(f"Created {len([review1, review2, review3, review4])} reviews.")

    print("\nDatabase seeding complete!")
    print("Sample Telegram IDs to test:")
    print(f"  Patient Alice: {user1.telegram_id} (has appointments, has given reviews)")
    print(f"  Patient Bob:   {user2.telegram_id} (has an appointment, has given reviews)")
    print(f"  Dr. Smith:     {user3_doc_smith.telegram_id} (is a Doctor)")
    print(f"  Dr. Jones:     {user4_doc_jones.telegram_id} (is a Doctor)")
    print(f"  New User Sam:  {user5_new.telegram_id} (will be prompted for name)")


if __name__ == "__main__":
    # This makes sure that the script can be run directly.
    # It will use the db_session from database.py which should be configured.

    # It's good practice to initialize the DB (create tables) if they don't exist
    # However, if you are running this after the bot has run, tables should exist.
    # For a standalone script, you might need:
    # from database import engine
    # Base.metadata.create_all(bind=engine)

    print("Starting database seeding process...")
    try:
        seed_database()
    except Exception as e:
        print(f"An error occurred during seeding: {e}")
        Session.rollback() # Rollback in case of error
    finally:
        Session.remove() # Close the session
        print("Seeding process finished.")
