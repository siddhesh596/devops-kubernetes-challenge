"""
DevOps Kubernetes Challenge API

A small, intentionally simple Task Management REST API used as the
application under test for a Kubernetes / CI-CD infrastructure challenge.
"""

import logging
import sys

from flask import Flask, jsonify, request, render_template

import database
from config import Config

# --- Logging setup -----------------------------------------------------
# Everything goes to stdout/stderr so `kubectl logs` can collect it later.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("devops_challenge_api")

ALLOWED_STATUSES = {"pending", "in-progress", "completed"}

app = Flask(__name__)


@app.before_request
def log_request():
    logger.info("%s %s", request.method, request.path)


# --- Error helpers -------------------------------------------------------

def error_response(message, status_code):
    return jsonify({"error": message}), status_code


@app.errorhandler(404)
def handle_404(e):
    return error_response("Not found", 404)


@app.errorhandler(405)
def handle_405(e):
    return error_response("Method not allowed", 405)


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    # Never leak stack traces or internal details to the client.
    logger.error("Unhandled application error", exc_info=True)
    return error_response("Internal server error", 500)


# --- Validation ------------------------------------------------------------

def validate_task_payload(data, partial=False):
    """Validate a create/update payload.

    Returns (cleaned_data, error_message). error_message is None on success.
    """
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object"

    title = data.get("title")
    description = data.get("description", "")
    status = data.get("status", "pending")

    if title is None or (isinstance(title, str) and title.strip() == ""):
        return None, "title is required"
    if not isinstance(title, str):
        return None, "title must be a string"
    if len(title) > 200:
        return None, "title maximum length is 200 characters"

    if description is not None and not isinstance(description, str):
        return None, "description must be a string"

    if status not in ALLOWED_STATUSES:
        return None, "status must be one of: pending, in-progress, completed"

    return {
        "title": title.strip(),
        "description": description or "",
        "status": status,
    }, None


# --- Routes ------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health():
    # Intentionally does NOT touch the database. Kubernetes uses this
    # to determine if the process itself is alive.
    return jsonify({"status": "healthy"}), 200


@app.route("/db-health", methods=["GET"])
def db_health():
    if database.check_connection():
        return jsonify({"status": "healthy", "database": "connected"}), 200
    return jsonify({"status": "unhealthy", "database": "disconnected"}), 503


@app.route("/tasks", methods=["GET"])
def list_tasks():
    try:
        tasks = database.fetch_all_tasks()
        return jsonify(tasks), 200
    except Exception:
        logger.error("Failed to fetch tasks", exc_info=True)
        return error_response("Database unavailable", 503)


@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    try:
        task = database.fetch_task(task_id)
    except Exception:
        logger.error("Failed to fetch task %s", task_id, exc_info=True)
        return error_response("Database unavailable", 503)

    if task is None:
        return error_response("Task not found", 404)
    return jsonify(task), 200


@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json(silent=True)
    cleaned, err = validate_task_payload(data)
    if err:
        return error_response(err, 400)

    try:
        task = database.create_task(
            cleaned["title"], cleaned["description"], cleaned["status"]
        )
        return jsonify(task), 201
    except Exception:
        logger.error("Failed to create task", exc_info=True)
        return error_response("Database unavailable", 503)


@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    data = request.get_json(silent=True)
    cleaned, err = validate_task_payload(data)
    if err:
        return error_response(err, 400)

    try:
        task = database.update_task(
            task_id, cleaned["title"], cleaned["description"], cleaned["status"]
        )
    except Exception:
        logger.error("Failed to update task %s", task_id, exc_info=True)
        return error_response("Database unavailable", 503)

    if task is None:
        return error_response("Task not found", 404)
    return jsonify(task), 200


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    try:
        deleted = database.delete_task(task_id)
    except Exception:
        logger.error("Failed to delete task %s", task_id, exc_info=True)
        return error_response("Database unavailable", 503)

    if not deleted:
        return error_response("Task not found", 404)
    return jsonify({"message": "Task deleted successfully"}), 200


def create_app():
    logger.info("Starting %s", Config.APP_NAME)
    database.init_db()
    return app


if __name__ == "__main__":
    application = create_app()
    logger.info("Application listening on 0.0.0.0:5000")
    application.run(host="0.0.0.0", port=5000)
