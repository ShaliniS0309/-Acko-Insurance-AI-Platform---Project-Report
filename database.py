# app/database.py
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, UUID, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid
from .config import Config

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100))
    email = Column(String(150), unique=True)
    phone = Column(String(15))
    role = Column(String(20), default='customer')
    created_at = Column(DateTime, default=datetime.now)

class Quotation(Base):
    __tablename__ = 'quotations'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True))
    vehicle_type = Column(String(10))
    vehicle_make = Column(String(50))
    vehicle_model = Column(String(80))
    manufacturing_year = Column(Integer)
    fuel_type = Column(String(20))
    city = Column(String(80))
    city_tier = Column(String(10))
    idv = Column(Float)
    ncb_percent = Column(Integer, default=0)
    predicted_premium = Column(Float)
    created_at = Column(DateTime, default=datetime.now)

class Claim(Base):
    __tablename__ = 'claims'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True))
    vehicle_type = Column(String(10))
    policy_number = Column(String(50))
    incident_date = Column(DateTime)
    damage_type = Column(String(50))
    damaged_parts = Column(String(200))
    severity = Column(String(20))
    image_url = Column(String(500))
    predicted_amount = Column(Float)
    approval_probability = Column(Float)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.now)

class ChatLog(Base):
    __tablename__ = 'chat_logs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True))
    intent = Column(String(30))
    question = Column(Text)
    answer = Column(Text)
    sources = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

# Database functions
def get_session():
    engine = create_engine(Config.DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def save_quotation(session, data):
    q = Quotation(**data)
    session.add(q)
    session.commit()
    return q

def save_claim(session, data):
    c = Claim(**data)
    session.add(c)
    session.commit()
    return c

def save_chat_log(session, data):
    log = ChatLog(**data)
    session.add(log)
    session.commit()
    return log

def get_dashboard_stats(session):
    from sqlalchemy import func
    stats = {
        'total_claims': session.query(func.count(Claim.id)).scalar() or 0,
        'car_claims': session.query(func.count(Claim.id)).filter(Claim.vehicle_type == 'car').scalar() or 0,
        'bike_claims': session.query(func.count(Claim.id)).filter(Claim.vehicle_type == 'bike').scalar() or 0,
        'avg_amount': session.query(func.avg(Claim.predicted_amount)).scalar() or 0,
        'total_quotations': session.query(func.count(Quotation.id)).scalar() or 0,
        'avg_premium': session.query(func.avg(Quotation.predicted_premium)).scalar() or 0,
    }
    # Approval rate
    approved = session.query(func.count(Claim.id)).filter(Claim.status == 'approved').scalar() or 0
    stats['approval_rate'] = (approved / stats['total_claims'] * 100) if stats['total_claims'] > 0 else 0
    return stats