"""Terminal HR assistant for employee profile lookups and confirmed updates."""

import re

from dotenv import load_dotenv

load_dotenv()

from hr_ai import interpret_request
from hr_records import (
    UPDATE_FIELDS,
    apply_employee_update,
    get_employee,
    get_employee_history,
    list_employees,
    list_employee_names,
    preview_employee_update,
    search_employees,
)


PROFILE_FIELDS = {
    "employee id": ("empId", "Employee ID"),
    "name": ("name", "Name"),
    "department": ("department", "Department"),
    "job title": ("designation", "Job title"),
    "work email": ("workEmail", "Work email"),
    "phone": ("phone", "Phone"),
    "manager": ("managerId", "Manager employee ID"),
    "joining date": ("joiningDate", "Joining date"),
}


def _display(value) -> str:
    if value is None or value == "":
        return "Not recorded"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def show_employee(employee: dict) -> None:
    print("\nEmployee record:")
    visible_employee = dict(employee)
    # Keep commonly maintained HR fields visible even before a value is recorded.
    for field in ("workEmail", "phone", "salary"):
        visible_employee.setdefault(field, None)
    for field, value in visible_employee.items():
        print(f"{field}: {_display(value)}")


def _show_matches(employees: list[dict]) -> None:
    if not employees:
        print("No matching employees found.")
        return
    print(f"\nMatches ({len(employees)}):")
    for employee in employees:
        print(
            f"{_display(employee.get('empId'))} | "
            f"{_display(employee.get('name'))} | "
            f"{_display(employee.get('department'))} | "
            f"{_display(employee.get('designation'))}"
        )
    if len(employees) == 25:
        print("Showing the first 25 results. Search with a more specific name or ID.")


def _resolve_employee(query: str) -> dict | None:
    query = (query or "").strip()
    if not query:
        print("Enter an employee ID or name.")
        return None
    if re.fullmatch(r"(?:EMP)?\d+", query, re.IGNORECASE):
        result = get_employee(query)
        if not result["ok"]:
            print(result["error"])
            return None
        return result["data"]

    result = search_employees(query)
    if not result["ok"]:
        print(result["error"])
        return None
    matches = result["data"]
    if not matches:
        print("No matching employees found.")
        return None
    if len(matches) == 1:
        selected = get_employee(matches[0]["empId"])
        if not selected["ok"]:
            print(selected["error"])
            return None
        return selected["data"]

    _show_matches(matches)
    selected_id = input("Enter the matching employee ID: ").strip()
    selected = get_employee(selected_id)
    if not selected["ok"]:
        print(selected["error"])
        return None
    if not any(item["empId"] == selected["data"]["empId"] for item in matches):
        print("Choose an ID from the displayed matches.")
        return None
    return selected["data"]


def search_flow(query: str | None = None) -> None:
    query = query if query is not None else input("Employee ID or name: ").strip()
    result = search_employees(query)
    if not result["ok"]:
        print(result["error"])
        return
    _show_matches(result["data"])


def list_names_flow() -> None:
    result = list_employee_names()
    if not result["ok"]:
        print(result["error"])
        return
    employees = result["data"]
    if not employees:
        print("No employee records found.")
        return
    print(f"\nEmployee names ({len(employees)}):")
    for employee in employees:
        print(_display(employee.get("name")))
    if len(employees) == 25:
        print("Showing the first 25 names.")


def list_employees_flow(fields: list[str] | None = None) -> None:
    result = list_employees(fields=fields)
    if not result["ok"]:
        print(result["error"])
        return
    employees = result["data"]
    if not employees:
        print("No employee records found.")
        return
    labels = " and ".join(fields) if fields else "all fields"
    print(f"\nEmployee records ({len(employees)}; showing {labels}):")
    for employee in employees:
        if fields:
            print("\n" + " | ".join(
                f"{field}: {_display(employee.get(field))}" for field in fields
            ))
        else:
            show_employee(employee)
    if len(employees) == 25:
        print("Showing the first 25 records.")


def view_flow(emp_id: str | None = None) -> None:
    emp_id = emp_id if emp_id is not None else input(
        "Employee ID (for example EMP102 or 102): "
    ).strip()
    result = get_employee(emp_id)
    if not result["ok"]:
        print(result["error"])
        return
    show_employee(result["data"])


def _normalise_update_field(field: str | None) -> str | None:
    if not isinstance(field, str):
        return None
    aliases = {
        "designation": "job title",
        "title": "job title",
        "email": "work email",
        "workemail": "work email",
        "work email address": "work email",
        "phone number": "phone",
        "mobile": "phone",
        "mobile number": "phone",
        "manager id": "manager",
        "managerid": "manager",
        "manager employee id": "manager",
        "department name": "department",
        "salary": "salary",
    }
    field = field.strip().casefold()
    field = aliases.get(field, field)
    return field if field in UPDATE_FIELDS else None


def update_flow(actor: str) -> None:
    emp_id = input("Employee ID (for example EMP102 or 102): ").strip()
    employee_result = get_employee(emp_id)
    if not employee_result["ok"]:
        print(employee_result["error"])
        return
    employee = employee_result["data"]
    print(f"\nUpdating {employee.get('name', 'employee')} ({employee['empId']})")

    fields = list(UPDATE_FIELDS.items())
    for number, (field, (database_field, label)) in enumerate(fields, start=1):
        print(f"{number}. {label} (current: {_display(employee.get(database_field))})")
    choice = input("Choose a field number: ").strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(fields):
        print("Choose one of the listed fields.")
        return

    field = fields[int(choice) - 1][0]
    raw_value = input("New value: ").strip()
    _confirm_update(emp_id, field, raw_value, actor, employee)


def _confirm_update(
    emp_id: str,
    field: str,
    raw_value: str,
    actor: str,
    employee: dict | None = None,
) -> None:
    preview = preview_employee_update(emp_id, field, raw_value)
    if not preview["ok"]:
        print(preview["error"])
        return
    change = preview["data"]
    employee = employee or get_employee(change["empId"]).get("data", {})
    print("\nProposed change")
    print(f"Employee: {employee.get('name', 'employee')} ({change['empId']})")
    print(f"Field: {change['label']}")
    print(f"From: {_display(change['oldValue'])}")
    print(f"To: {_display(change['newValue'])}")
    confirmation = input("Type YES to save this change: ").strip()
    if confirmation.casefold() != "yes":
        print("Update cancelled.")
        return

    result = apply_employee_update(
        emp_id=change["empId"],
        field=field,
        new_value=change["newValue"],
        expected_old_value=change["oldValue"],
        actor=actor,
    )
    if not result["ok"]:
        print(result["error"])
        return
    if not result["data"]["changed"]:
        print("No update was needed; the value is already current.")
        return
    print(f"Saved. Audit reference: {result['data']['changeId']}")


def history_flow(emp_id: str | None = None) -> None:
    emp_id = emp_id if emp_id is not None else input(
        "Employee ID or name: "
    ).strip()
    employee = _resolve_employee(emp_id)
    if employee is None:
        return
    result = get_employee_history(employee["empId"])
    if not result["ok"]:
        print(result["error"])
        return
    entries = result["data"]
    if not entries:
        print(f"No recorded changes for {employee.get('name')} ({employee['empId']}).")
        return
    print(f"\nRecent changes for {employee.get('name')} ({employee['empId']}):")
    for entry in entries:
        print(
            f"{_display(entry.get('changedAt'))} | {entry.get('label', entry.get('field'))} | "
            f"{_display(entry.get('oldValue'))} -> {_display(entry.get('newValue'))} | "
            f"by {entry.get('changedBy', 'unknown')} | {entry.get('changeId', '')}"
        )


def _looks_like_update(question: str) -> bool:
    if re.search(r"\b(history|previous|recent|changes? made|who changed|who updated)\b", question, re.IGNORECASE):
        return False
    return bool(
        re.search(
            r"\b(update\w*|change\w*|edit\w*|set|correct\w*|replace\w*|"
            r"move\w*|assign\w*|modify\w*|transfer\w*|switch\w*|revise\w*|promot\w*)\b",
            question,
            re.IGNORECASE,
        )
    )


def ask_hr_flow(actor: str) -> None:
    question = input("HR question: ").strip()
    if not question:
        return
    if _looks_like_employee_roster_request(question):
        fields = _requested_roster_fields(question)
        list_employees_flow(fields=fields)
        return
    result = interpret_request(question)
    if not isinstance(result, dict) or not result.get("ok"):
        print(
            result.get("error", "The request could not be interpreted. Try a direct menu option.")
            if isinstance(result, dict)
            else "The request could not be interpreted. Try a direct menu option."
        )
        return
    request = result["data"]
    action = request["action"]
    query = request.get("employee_query")
    if action == "list_employees":
        list_employees_flow()
        return
    if action == "list_names":
        list_names_flow()
        return
    if action == "search":
        search_flow(query)
        return
    if action == "update":
        field = _normalise_update_field(request.get("field"))
        if field is None:
            print("That field cannot be changed through this HR workflow.")
            return
        employee = _resolve_employee(query or "")
        if employee is None:
            return
        _confirm_update(employee["empId"], field, request["value"], actor, employee)
        return
    if action == "unsupported":
        print(
            "I can search employees, view all fields in employee records, and show change history. "
            "Use option 4 for a confirmed profile update."
        )
        return

    employee = _resolve_employee(query or "")
    if employee is None:
        return
    if action == "view":
        show_employee(employee)
    elif action == "history":
        history_flow(employee["empId"])
    elif action == "field_question":
        field = request.get("field")
        if field == "all":
            show_employee(employee)
            return
        field_key = (field or "").replace(" ", "").casefold()
        selected = next(
            ((key, label) for key, label in ((key, key) for key in employee)
             if key.replace("_", "").casefold() == field_key),
            None,
        )
        if selected is None:
            print("That field was not found in the employee record.")
            return
        database_field, label = selected
        print(f"{label} for {employee.get('name')} ({employee.get('empId')}): {_display(employee.get(database_field))}")


def _looks_like_employee_roster_request(value: str) -> bool:
    return bool(
        re.search(r"\b(all|every|list)\b", value, re.IGNORECASE)
        and re.search(r"\b(employee|employees|staff|people|personnel)\b", value, re.IGNORECASE)
    )


def _requested_roster_fields(question: str) -> list[str] | None:
    """Map common roster field words to actual MongoDB document keys."""
    lowered = question.casefold()
    requested = []
    aliases = {
        "empId": ("employee id", "employee ids", "empid"),
        "name": ("name", "names"),
        "salary": ("salary", "salaries", "pay", "compensation"),
    }
    for field, terms in aliases.items():
        if any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in terms):
            requested.append(field)
    return requested or None


def main() -> None:
    print("HR Helpdesk — employee records")
    try:
        actor = ""
        while not actor:
            actor = input("HR operator name for the audit log: ").strip()
            if not actor:
                print("Enter your name to continue.")
            elif _looks_like_employee_roster_request(actor):
                actor = ""
                print("That looks like an HR question. Enter your name here; you can ask the question after choosing option 1.")
        print("\n1. Ask a natural-language HR question")
        print("2. Search employees")
        print("3. View an employee")
        print("4. Update a basic profile field")
        print("5. View employee change history")
        print("6. Exit")
        while True:
            choice = input("\nSelect an option: ").strip()
            if choice == "1":
                ask_hr_flow(actor)
            elif choice == "2":
                search_flow()
            elif choice == "3":
                view_flow()
            elif choice == "4":
                update_flow(actor)
            elif choice == "5":
                history_flow()
            elif choice == "6" or choice.casefold() in {"exit", "quit", "q"}:
                print("Goodbye.")
                return
            else:
                print("Choose 1, 2, 3, 4, 5, or 6.")
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")


if __name__ == "__main__":
    main()
