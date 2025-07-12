from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Enum as SQLAlchemyEnum, Time
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class UserRole(enum.Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True) # Telegram username
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.PATIENT, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    appointments = relationship("Appointment", back_populates="user")
    reviews_given = relationship("Review", back_populates="user")

    # For doctors, this will link to their specific doctor profile
    doctor_profile = relationship("Doctor", uselist=False, back_populates="user_account")


class Specialty(Base):
    __tablename__ = "specialties"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    doctors = relationship("Doctor", secondary="doctor_specialties", back_populates="specialties")

class DoctorSpecialty(Base):
    __tablename__ = "doctor_specialties"
    doctor_id = Column(Integer, ForeignKey("doctors.id"), primary_key=True)
    specialty_id = Column(Integer, ForeignKey("specialties.id"), primary_key=True)


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False) # Link to the User table
    bio = Column(String, nullable=True) # A short bio or description
    # Add other doctor-specific fields if needed, e.g., consultation_fee

    user_account = relationship("User", back_populates="doctor_profile")
    schedules = relationship("DoctorSchedule", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")
    reviews_received = relationship("Review", back_populates="doctor")
    specialties = relationship("Specialty", secondary="doctor_specialties", back_populates="doctors")


    def __repr__(self):
        return f"<Doctor(id={self.id}, user_id={self.user_id})>"

class DoctorSchedule(Base):
    __tablename__ = "doctor_schedules"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    available_date = Column(DateTime, nullable=False) # Store as DateTime for consistency, can extract date part
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_booked = Column(Integer, default=0) # 0 for false, 1 for true, or use Boolean if db supports it well

    doctor = relationship("Doctor", back_populates="schedules")

    def __repr__(self):
        return f"<DoctorSchedule(doctor_id={self.doctor_id}, date='{self.available_date}', start='{self.start_time}', end='{self.end_time}')>"


class AppointmentStatus(enum.Enum):
    SCHEDULED = "scheduled"
    CANCELLED_BY_USER = "cancelled_by_user"
    CANCELLED_BY_DOCTOR = "cancelled_by_doctor"
    COMPLETED = "completed"

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("doctor_schedules.id"), nullable=True) # Link to the specific schedule slot
    appointment_time = Column(DateTime, nullable=False) # Specific time of the appointment
    status = Column(SQLAlchemyEnum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    # schedule_slot = relationship("DoctorSchedule") # If needed

    def __repr__(self):
        return f"<Appointment(id={self.id}, user_id={self.user_id}, doctor_id={self.doctor_id}, time='{self.appointment_time}')>"

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # User who wrote the review
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False) # Doctor being reviewed
    rating = Column(Integer, nullable=False) # e.g., 1 to 5
    comment = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="reviews_given")
    doctor = relationship("Doctor", back_populates="reviews_received")

    def __repr__(self):
        return f"<Review(id={self.id}, user_id={self.user_id}, doctor_id={self.doctor_id}, rating={self.rating})>"

# Example of how to create the engine and tables (this would typically be in database.py or main bot file)
if __name__ == "__main__":
    from sqlalchemy import create_engine
    from config import DATABASE_URI

    engine = create_engine(DATABASE_URI)
    Base.metadata.create_all(bind=engine)
    print("Database tables created (if they didn't exist).")
