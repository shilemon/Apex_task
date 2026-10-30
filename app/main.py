"""Apex Operations API - small incident-tracking service (synthetic data only)."""
import json
import logging
import os
import sys
import time
import uuid
from typing import List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import Base, Incident, engine, get_db

APP_VERSION = os.getenv("APP_VERSION", "dev")


# ---------- structured (JSON) logging ----------
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "msg": record.getMessage(),
            "version": APP_VERSION,
        }
        payload.update(getattr(record, "extra_fields", {}))
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(JsonFormatter())
log = logging.getLogger("apex")
log.handlers = [_handler]
log.setLevel(os.getenv("LOG_LEVEL", "INFO"))
log.propagate = False


def jlog(level: int, msg: str, **fields):
    log.log(level, msg, extra={"extra_fields": fields})


# ---------- metrics ----------
REQUESTS = Counter("apex_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("apex_http_request_seconds", "Request latency", ["path"])
DB_UP = Gauge("apex_db_up", "1 if the database answered the last readiness check")

app = FastAPI(title="Apex Operations API", version=APP_VERSION)


@app.on_event("startup")
def startup() -> None:
    # Retry so the API survives a slow-starting database.
    for attempt in range(1, 11):
        try:
            Base.metadata.create_all(bind=engine)
            jlog(logging.INFO, "startup_ok", attempt=attempt)
            return
        except Exception as exc:  # noqa: BLE001
            jlog(logging.WARNING, "startup_db_retry", attempt=attempt, error=str(exc)[:200])
            time.sleep(2)
    jlog(logging.ERROR, "startup_db_unavailable")


@app.middleware("http")
async def observe(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    route = request.scope.get("route")
    path = route.path if route else request.url.path
    REQUESTS.labels(request.method, path, response.status_code).inc()
    LATENCY.labels(path).observe(elapsed)
    response.headers["x-request-id"] = request_id
    if path not in ("/metrics", "/health"):
        jlog(
            logging.INFO,
            "request",
            request_id=request_id,
            method=request.method,
            path=path,
            status=response.status_code,
            duration_ms=round(elapsed * 1000, 2),
        )
    return response


# ---------- schemas ----------
class IncidentIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    severity: Literal["low", "medium", "high", "critical"]


class IncidentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    severity: Optional[Literal["low", "medium", "high", "critical"]] = None
    status: Optional[Literal["open", "resolved"]] = None


class IncidentOut(BaseModel):
    id: int
    title: str
    severity: str
    status: str

    class Config:
        from_attributes = True


# ---------- operational endpoints ----------
@app.get("/health")
def health():
    """Liveness: the process is up. Does not touch dependencies."""
    return {"status": "ok", "version": APP_VERSION}


@app.get("/readiness")
@app.get("/ready", include_in_schema=False)  # short alias kept for convenience
def ready(response: Response, db: Session = Depends(get_db)):
    """Readiness: can we serve traffic? Checks the database."""
    try:
        db.execute(text("SELECT 1"))
        DB_UP.set(1)
        return {"status": "ready", "database": "up"}
    except Exception as exc:  # noqa: BLE001
        DB_UP.set(0)
        jlog(logging.ERROR, "db_unavailable", error=str(exc)[:200])
        response.status_code = 503
        return {"status": "not_ready", "database": "down"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---------- business endpoints ----------
@app.post("/api/v1/incidents", response_model=IncidentOut, status_code=201)
def create_incident(body: IncidentIn, db: Session = Depends(get_db)):
    inc = Incident(title=body.title, severity=body.severity, status="open")
    db.add(inc)
    db.commit()
    db.refresh(inc)
    return inc


@app.get("/api/v1/incidents", response_model=List[IncidentOut])
def list_incidents(db: Session = Depends(get_db)):
    return db.query(Incident).order_by(Incident.id).all()


@app.get("/api/v1/incidents/{incident_id}", response_model=IncidentOut)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    inc = db.get(Incident, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="incident not found")
    return inc


@app.put("/api/v1/incidents/{incident_id}", response_model=IncidentOut)
def update_incident(incident_id: int, body: IncidentUpdate, db: Session = Depends(get_db)):
    inc = db.get(Incident, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="incident not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(inc, field, value)
    db.commit()
    db.refresh(inc)
    return inc


@app.delete("/api/v1/incidents/{incident_id}", status_code=204)
def delete_incident(incident_id: int, db: Session = Depends(get_db)):
    inc = db.get(Incident, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="incident not found")
    db.delete(inc)
    db.commit()
    return Response(status_code=204)


@app.post("/api/v1/incidents/{incident_id}/resolve", response_model=IncidentOut)
def resolve_incident(incident_id: int, db: Session = Depends(get_db)):
    inc = db.get(Incident, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="incident not found")
    inc.status = "resolved"
    db.commit()
    db.refresh(inc)
    return inc
