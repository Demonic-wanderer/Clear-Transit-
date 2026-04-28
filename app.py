from __future__ import annotations

from functools import wraps
from pathlib import Path
import os
import secrets

from flask import Flask, jsonify, redirect, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from Records.models import SessionLocal, User
from pipeline.config import get_settings
from pipeline.relocation import relocate_route
from pipeline.service import build_dashboard_snapshot, ensure_bootstrap, run_monitoring_cycle
from pipeline.shipments import (
    create_shipment,
    list_shipments,
    reset_seed_shipments,
    reroute_shipment,
    shipment_options,
    update_shipment,
)


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "Frontend"
SETTINGS = get_settings()

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="/static")
app.config["SECRET_KEY"] = SETTINGS.secret_key or secrets.token_hex(32)
ensure_bootstrap()


def _is_api_request() -> bool:
    return request.path.startswith("/api/")


def _get_current_user() -> User | None:
    user_id = session.get("user_id")
    if not user_id:
        return None

    with SessionLocal() as db:
        return db.query(User).filter_by(id=user_id).first()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = _get_current_user()
        if user is None:
            if _is_api_request():
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("login_page"))
        return view(*args, **kwargs)

    return wrapped


def _read_auth_payload() -> tuple[str, str, str | None]:
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    full_name = payload.get("full_name")
    full_name = str(full_name).strip() if full_name is not None else None
    return email, password, full_name


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"status": "ok"}, 200


@app.get("/login")
def login_page() -> object:
    if _get_current_user():
        return redirect(url_for("index"))
    return send_from_directory(FRONTEND_DIR, "auth.html")


@app.get("/shipments")
@login_required
def shipments_page() -> object:
    return send_from_directory(FRONTEND_DIR, "shipments.html")


@app.get("/auth.js")
def auth_js() -> object:
    return send_from_directory(FRONTEND_DIR, "auth.js")


@app.get("/auth.css")
def auth_css() -> object:
    return send_from_directory(FRONTEND_DIR, "auth.css")


@app.get("/api/auth/me")
def auth_me() -> tuple[object, int]:
    user = _get_current_user()
    if user is None:
        return jsonify({"authenticated": False}), 200
    return jsonify({"authenticated": True, "user": user.to_dict()}), 200


@app.post("/api/auth/register")
def auth_register() -> tuple[object, int]:
    email, password, full_name = _read_auth_payload()

    if not full_name or not email or not password:
        return jsonify({"error": "Full name, email, and password are required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    with SessionLocal() as db:
        existing_user = db.query(User).filter_by(email=email).first()
        if existing_user is not None:
            return jsonify({"error": "An account with this email already exists"}), 409

        user = User(
            email=email,
            full_name=full_name,
            password_hash=generate_password_hash(password, method="pbkdf2:sha256"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        session["user_id"] = user.id
        return jsonify({"user": user.to_dict()}), 201


@app.post("/api/auth/login")
def auth_login() -> tuple[object, int]:
    email, password, _ = _read_auth_payload()

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    with SessionLocal() as db:
        user = db.query(User).filter_by(email=email).first()
        if user is None or not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid email or password"}), 401

        session["user_id"] = user.id
        return jsonify({"user": user.to_dict()}), 200


@app.post("/api/auth/logout")
def auth_logout() -> tuple[object, int]:
    session.clear()
    return jsonify({"ok": True}), 200


@app.get("/api/dashboard")
@login_required
def dashboard() -> tuple[object, int]:
    return jsonify(build_dashboard_snapshot()), 200


@app.get("/api/shipments")
@login_required
def shipments() -> tuple[object, int]:
    return jsonify({"shipments": list_shipments(), "options": shipment_options()}), 200


@app.post("/api/shipments")
@login_required
def create_shipments() -> tuple[object, int]:
    payload = request.get_json(silent=True) or {}
    try:
        shipment = create_shipment(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"shipment": shipment, "shipments": list_shipments()}), 201


@app.patch("/api/shipments/<route_id>")
@login_required
def update_shipments(route_id: str) -> tuple[object, int]:
    payload = request.get_json(silent=True) or {}
    try:
        shipment = update_shipment(route_id, payload)
    except ValueError as exc:
        status = 404 if str(exc) == "Shipment not found" else 400
        return jsonify({"error": str(exc)}), status
    return jsonify({"shipment": shipment, "shipments": list_shipments()}), 200


@app.post("/api/shipments/seed")
@login_required
def reseed_shipments() -> tuple[object, int]:
    shipments = reset_seed_shipments()
    return jsonify({"shipments": shipments, "message": "Restored the 10-shipment Indore database."}), 200


@app.post("/api/shipments/<route_id>/reroute")
@login_required
def reroute_shipment_page(route_id: str) -> tuple[object, int]:
    payload = request.get_json(silent=True) or {}
    try:
        shipment = reroute_shipment(route_id, payload.get("reason", "shipment database operator action"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"shipment": shipment, "shipments": list_shipments()}), 200


@app.post("/api/refresh")
@login_required
def refresh() -> tuple[object, int]:
    payload = request.get_json(silent=True) or {}
    snapshot = run_monitoring_cycle(apply_relocation=bool(payload.get("apply_relocation", False)))
    return jsonify(snapshot), 200


@app.post("/api/routes/<route_id>/reroute")
@login_required
def reroute(route_id: str) -> tuple[object, int]:
    payload = request.get_json(silent=True) or {}

    try:
        route = relocate_route(route_id, reason=payload.get("reason", "manual intervention"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    snapshot = build_dashboard_snapshot()
    snapshot["last_action"] = route
    return jsonify(snapshot), 200


@app.get("/")
@login_required
def index() -> object:
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/app.js")
def app_js() -> object:
    return send_from_directory(FRONTEND_DIR, "app.js")


@app.get("/style.css")
def style_css() -> object:
    return send_from_directory(FRONTEND_DIR, "style.css")


@app.get("/shipments.js")
def shipments_js() -> object:
    return send_from_directory(FRONTEND_DIR, "shipments.js")


@app.get("/shipments.css")
def shipments_css() -> object:
    return send_from_directory(FRONTEND_DIR, "shipments.css")


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
