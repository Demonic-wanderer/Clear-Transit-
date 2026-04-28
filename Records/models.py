import os
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Column, Integer, String, Float, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True)
    route_id = Column(String, unique=True, nullable=False)
    shipment_id = Column(String)
    vehicle_label = Column(String)
    source = Column(String)
    destination = Column(String)
    distance_km = Column(Float)
    eta_minutes = Column(Integer)
    load_tons = Column(Float)
    status = Column(String)
    progress_ratio = Column(Float)
    base_risk_score = Column(Integer)
    risk_score = Column(Integer)
    
    cargo_type = Column(String)
    cargo_value_usd = Column(Integer)
    telemetry_temperature_c = Column(Float)
    telemetry_status = Column(String)
    
    current_lat = Column(Float)
    current_lon = Column(Float)
    dest_lat = Column(Float)
    dest_lon = Column(Float)
    
    last_action = Column(String, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "shipment_id": self.shipment_id,
            "vehicle_label": self.vehicle_label,
            "source": self.source,
            "destination": self.destination,
            "distance_km": self.distance_km,
            "eta_minutes": self.eta_minutes,
            "load_tons": self.load_tons,
            "status": self.status,
            "progress_ratio": self.progress_ratio,
            "base_risk_score": self.base_risk_score,
            "risk_score": self.risk_score,
            "cargo_type": self.cargo_type,
            "cargo_value_usd": self.cargo_value_usd,
            "telemetry_temperature_c": self.telemetry_temperature_c,
            "telemetry_status": self.telemetry_status,
            "current_location": {"lat": self.current_lat, "lon": self.current_lon},
            "destination_location": {"lat": self.dest_lat, "lon": self.dest_lon},
            "last_action": self.last_action,
        }

class DisruptionEvent(Base):
    __tablename__ = "disruption_events"

    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False)
    timestamp = Column(String, default=_iso_now)
    severity = Column(String)
    summary = Column(String)
    location = Column(String)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "severity": self.severity,
            "summary": self.summary,
            "location": self.location,
        }


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
        }

# Setup Database Connection
DB_PATH = os.path.join(os.path.dirname(__file__), "alerts.db")
engine = create_engine(f"sqlite:///{DB_PATH}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db() -> None:
    from sqlalchemy import inspect
    inspector = inspect(engine)
    if inspector.has_table("routes"):
        columns = [col['name'] for col in inspector.get_columns("routes")]
        if "cargo_type" not in columns:
            print("Schema change detected. Dropping old tables to recreate...")
            Base.metadata.drop_all(bind=engine)
            
    Base.metadata.create_all(bind=engine)
