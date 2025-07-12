import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram_bot_project.database import db_session
from telegram_bot_project.models import Doctor, User

def verify():
    """Queries and prints the list of doctors."""
    print("Verifying doctors in the database...")
    doctors = db_session.query(Doctor).join(User, Doctor.user_id == User.id).all()
    if not doctors:
        print("No doctors found in the database.")
    else:
        print(f"Found {len(doctors)} doctors:")
        for doc in doctors:
            print(f"  - Dr. {doc.user_account.first_name} {doc.user_account.last_name} - {doc.specialty}")

if __name__ == "__main__":
    verify()
