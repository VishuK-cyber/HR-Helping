"""Small, deterministic MongoDB operations for the HR terminal MVP."""

import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient
from pymongo.errors import CollectionInvalid


EMPLOYEE_FIELDS = (
    "empId",
    "name",
    "department",
    "designation",
    "workEmail",
    "phone",
    "managerId",
    "joiningDate",
)
UPDATE_FIELDS = {
    "department": ("department", "Department"),
    "job title": ("designation", "Job title"),
    "work email": ("workEmail", "Work email"),
    "phone": ("phone", "Phone"),
    "manager": ("managerId", "Manager employee ID"),
    "salary": ("salary", "Salary"),
}

_mongo_client: MongoClient | None = None


def _success(data: Any) -> dict:
    return {"ok": True, "data": data}


def _error(code: str, message: str) -> dict:
    return {"ok": False, "error_code": code, "error": message}


def _get_client() -> MongoClient:
    global _mongo_client
    uri = (os.getenv("MONGODB_URI") or "").strip()
    if not uri:
        raise ValueError("MONGODB_URI is not configured.")
    if _mongo_client is None:
        _mongo_client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return _mongo_client


def _get_db():
    db_name = (os.getenv("MONGODB_DB_NAME") or "hr_helpdesk").strip()
    return _get_client()[db_name]


def _ensure_audit_collection(db) -> None:
    try:
        db.create_collection("employeeChangeLog")
    except CollectionInvalid:
        pass


def _projection() -> dict:
    # HR read access covers every employee document field. Omit only Mongo's internal ID.
    return {"_id": 0}


def _normalise_employee_id(emp_id: str) -> str:
    value = emp_id.strip().upper()
    return f"EMP{value}" if value.isdigit() else value


def search_employees(query: str) -> dict:
    """Search a small set of employee profile fields by ID or name."""
    if not isinstance(query, str) or not query.strip():
        return _error("INVALID_INPUT", "Enter an employee ID or name to search.")
    try:
        pattern = re.escape(query.strip())
        employees = _get_db()["employees"]
        results = list(
            employees.find(
                {
                    "$or": [
                        {"empId": {"$regex": pattern, "$options": "i"}},
                        {"name": {"$regex": pattern, "$options": "i"}},
                    ]
                },
                _projection(),
            )
            .sort("empId", 1)
            .limit(25)
        )
        return _success(results)
    except Exception:
        return _error("DB_ERROR", "Could not search employee records. Check the database connection.")


def list_employee_names(limit: int = 25) -> dict:
    """Return a bounded, name-only list for the HR roster request."""
    try:
        employees = _get_db()["employees"]
        results = list(
            employees.find({}, {"empId": 1, "name": 1, "_id": 0})
            .sort("empId", 1)
            .limit(max(1, min(int(limit), 100)))
        )
        return _success(results)
    except Exception:
        return _error("DB_ERROR", "Could not retrieve employee names. Check the database connection.")


def list_employees(limit: int = 25, fields: list[str] | None = None) -> dict:
    """Return a bounded set of employee documents, optionally with selected fields."""
    try:
        employees = _get_db()["employees"]
        projection = {"_id": 0}
        if fields:
            projection.update({field: 1 for field in fields})
        results = list(
            employees.find({}, projection)
            .sort("empId", 1)
            .limit(max(1, min(int(limit), 100)))
        )
        return _success(results)
    except Exception:
        return _error("DB_ERROR", "Could not retrieve employee records. Check the database connection.")


def get_employee(emp_id: str) -> dict:
    if not isinstance(emp_id, str) or not emp_id.strip():
        return _error("INVALID_INPUT", "Enter an employee ID.")
    try:
        normalized_id = _normalise_employee_id(emp_id)
        employee = _get_db()["employees"].find_one(
            {"empId": normalized_id}, _projection()
        )
        if employee is None:
            return _error("UNKNOWN_EMPLOYEE", f"Employee {normalized_id} was not found.")
        return _success(employee)
    except Exception:
        return _error("DB_ERROR", "Could not retrieve the employee record. Check the database connection.")


def get_employee_history(emp_id: str, limit: int = 20) -> dict:
    if not isinstance(emp_id, str) or not emp_id.strip():
        return _error("INVALID_INPUT", "Enter an employee ID.")
    try:
        normalized_id = _normalise_employee_id(emp_id)
        db = _get_db()
        employee = db["employees"].find_one(
            {"empId": normalized_id}, {"empId": 1, "name": 1, "_id": 0}
        )
        if employee is None:
            return _error("UNKNOWN_EMPLOYEE", f"Employee {normalized_id} was not found.")
        changes = list(
            db["employeeChangeLog"]
            .find({"empId": normalized_id}, {"_id": 0})
            .sort("changedAt", -1)
            .limit(max(1, min(int(limit), 100)))
        )
        return _success(changes)
    except Exception:
        return _error("DB_ERROR", "Could not retrieve the employee change history.")


def _normalise_field(field: str) -> tuple[str, str] | None:
    if not isinstance(field, str):
        return None
    return UPDATE_FIELDS.get(field.strip().casefold())


def _normalise_value(field_name: str, raw_value: str) -> tuple[bool, Any, str | None]:
    if not isinstance(raw_value, str):
        return False, None, "Enter the new value as text."
    value = raw_value.strip()
    if field_name == "managerId" and value.casefold() in {"none", "unassigned"}:
        return True, None, None
    if not value:
        return False, None, "The value cannot be empty. Use 'none' to clear the manager."
    if len(value) > 120 or any(character in value for character in "\r\n\x00"):
        return False, None, "Use a single-line value of at most 120 characters."
    if field_name == "workEmail":
        if len(value) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            return False, None, "Enter a valid work email address."
        return True, value, None
    if field_name == "phone":
        digits = re.sub(r"\D", "", value)
        if not re.fullmatch(r"[+0-9(). -]+", value) or not 7 <= len(digits) <= 15:
            return False, None, "Enter a phone number with 7 to 15 digits."
        return True, value, None
    if field_name == "managerId":
        manager_id = _normalise_employee_id(value)
        if not re.fullmatch(r"EMP[A-Z0-9-]{1,24}", manager_id):
            return False, None, "Enter a valid manager employee ID, or 'none'."
        return True, manager_id, None
    if field_name.casefold() == "salary":
        try:
            amount = float(value.replace(",", "").replace("$", "").strip())
            if amount < 0:
                raise ValueError
            return (True, int(amount), None) if amount.is_integer() else (True, amount, None)
        except ValueError:
            return False, None, "Enter a valid non-negative salary amount."
    return True, value, None


def _manager_exists(employees, manager_id: str | None, employee_id: str, session=None) -> bool:
    if manager_id is None:
        return True
    if manager_id == employee_id:
        return False
    return employees.find_one(
        {"empId": manager_id}, {"_id": 1}, session=session
    ) is not None


def preview_employee_update(emp_id: str, field: str, raw_value: str) -> dict:
    """Validate an update and return the current and proposed values for review."""
    selected_field = _normalise_field(field)
    if selected_field is None:
        return _error("FIELD_NOT_ALLOWED", "That profile field cannot be changed here.")
    field_name, label = selected_field
    valid, new_value, validation_error = _normalise_value(field_name, raw_value)
    if not valid:
        return _error("INVALID_VALUE", validation_error or "The value is invalid.")

    employee_result = get_employee(emp_id)
    if not employee_result["ok"]:
        return employee_result
    normalized_id = _normalise_employee_id(emp_id)
    try:
        if field_name == "managerId" and not _manager_exists(
            _get_db()["employees"], new_value, normalized_id
        ):
            return _error("INVALID_MANAGER", "Choose a different existing employee as manager.")
        employee = employee_result["data"]
        return _success(
            {
                "empId": normalized_id,
                "field": field_name,
                "label": label,
                "oldValue": employee.get(field_name),
                "newValue": new_value,
            }
        )
    except Exception:
        return _error("DB_ERROR", "Could not validate the proposed update.")


def apply_employee_update(
    emp_id: str,
    field: str,
    new_value: Any,
    expected_old_value: Any,
    actor: str,
) -> dict:
    """Atomically update one allowed field and append its audit record."""
    selected_field = _normalise_field(field)
    if selected_field is None:
        return _error("FIELD_NOT_ALLOWED", "That profile field cannot be changed here.")
    if not isinstance(actor, str) or not actor.strip() or len(actor.strip()) > 100:
        return _error("INVALID_ACTOR", "Enter an HR operator name for the audit record.")

    field_name, label = selected_field
    if new_value is None and field_name != "managerId":
        return _error("INVALID_VALUE", "Only the manager field can be cleared.")
    if new_value is not None:
        valid, normalised_value, validation_error = _normalise_value(field_name, str(new_value))
        if not valid:
            return _error("INVALID_VALUE", validation_error or "The value is invalid.")
        new_value = normalised_value

    normalized_id = _normalise_employee_id(emp_id)
    try:
        client = _get_client()
        db = _get_db()
        _ensure_audit_collection(db)
        with client.start_session() as session:
            with session.start_transaction():
                employees = db["employees"]
                current = employees.find_one(
                    {"empId": normalized_id}, _projection(), session=session
                )
                if current is None:
                    return _error("UNKNOWN_EMPLOYEE", f"Employee {normalized_id} was not found.")
                old_value = current.get(field_name)
                if old_value != expected_old_value:
                    return _error(
                        "RECORD_CHANGED",
                        "This field changed after the preview. Review the current record and try again.",
                    )
                if field_name == "managerId" and not _manager_exists(
                    employees, new_value, normalized_id, session=session
                ):
                    return _error("INVALID_MANAGER", "Choose a different existing employee as manager.")
                if old_value == new_value:
                    return _success({"changed": False, "empId": normalized_id})

                changed_at = datetime.now(timezone.utc)
                change_id = f"CHG-{uuid.uuid4().hex[:12].upper()}"
                update_result = employees.update_one(
                    {"empId": normalized_id},
                    {"$set": {field_name: new_value}},
                    session=session,
                )
                if update_result.matched_count != 1:
                    return _error("UNKNOWN_EMPLOYEE", f"Employee {normalized_id} was not found.")
                db["employeeChangeLog"].insert_one(
                    {
                        "changeId": change_id,
                        "empId": normalized_id,
                        "employeeName": current.get("name"),
                        "field": field_name,
                        "label": label,
                        "oldValue": old_value,
                        "newValue": new_value,
                        "changedBy": actor.strip(),
                        "changedAt": changed_at,
                    },
                    session=session,
                )
        return _success(
            {
                "changed": True,
                "changeId": change_id,
                "empId": normalized_id,
                "field": field_name,
                "oldValue": old_value,
                "newValue": new_value,
                "changedAt": changed_at.isoformat(),
            }
        )
    except Exception:
        return _error(
            "DB_ERROR",
            "The update could not be confirmed. Check the employee record and audit log before retrying.",
        )
