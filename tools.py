from __future__ import annotations

from datetime import date, datetime
from typing import Any

from db import get_db


def getLeaveBalance(empId: str) -> dict[str, Any]:
    """Return remaining leave = total - used for each leave type."""
    db = get_db()
    docs = list(db.leaves.find({"empId": empId}, {"_id": 0, "type": 1, "total": 1, "used": 1}))

    balances = {}
    total_remaining = 0
    for doc in docs:
        remaining = max(0, int(doc.get("total", 0)) - int(doc.get("used", 0)))
        balances[doc.get("type", "unknown")] = remaining
        total_remaining += remaining

    return {
        "empId": empId,
        "balances": balances,
        "totalRemaining": total_remaining,
    }


def getPayslip(empId: str, month: str, authorized_emp_id: str) -> dict[str, Any]:
    """Return a payslip only for the logged-in employee."""
    if empId != authorized_emp_id:
        return {"error": "PRIVACY_DENIED", "message": "You can only access your own payslip."}

    normalized = normalize_month(month)
    db = get_db()
    doc = db.payroll.find_one({"empId": empId, "month": normalized}, {"_id": 0})

    if not doc:
        return {
            "empId": empId,
            "month": normalized,
            "found": False,
            "message": "No payslip was found for that month.",
        }

    return {"found": True, **doc}


def searchPolicy(keyword: str) -> dict[str, Any]:
    """Search policy text and return at most two matching entries."""
    db = get_db()
    docs = list(
        db.policies.find(
            {"$text": {"$search": keyword}},
            {"_id": 0, "score": {"$meta": "textScore"}, "policyId": 1, "title": 1, "category": 1, "content": 1, "keywords": 1},
        )
        .sort([("score", {"$meta": "textScore"})])
        .limit(2)
    )

    for doc in docs:
        doc.pop("score", None)

    return {"keyword": keyword, "count": len(docs), "policies": docs}


def applyLeave(
    empId: str,
    fromDate: str,
    toDate: str,
    reason: str,
    authorized_emp_id: str,
) -> dict[str, Any]:
    """Create a leave request after checking the employee's available balance."""
    if empId != authorized_emp_id:
        return {"error": "PRIVACY_DENIED", "message": "You can only apply leave for yourself."}

    try:
        start = date.fromisoformat(fromDate)
        end = date.fromisoformat(toDate)
    except ValueError:
        return {"error": "INVALID_DATE", "message": "Dates must use YYYY-MM-DD."}

    if end < start:
        return {"error": "INVALID_RANGE", "message": "toDate cannot be before fromDate."}

    requested_days = (end - start).days + 1
    balance = getLeaveBalance(empId)

    if balance["totalRemaining"] < requested_days:
        return {
            "error": "INSUFFICIENT_BALANCE",
            "requestedDays": requested_days,
            "availableDays": balance["totalRemaining"],
            "message": "Leave request refused because the available leave balance is insufficient.",
        }

    db = get_db()
    existing = db.leaveRequests.find_one(
        {
            "empId": empId,
            "fromDate": fromDate,
            "toDate": toDate,
            "status": {"$in": ["pending", "approved"]},
        }
    )
    if existing:
        return {
            "error": "DUPLICATE_REQUEST",
            "requestId": existing.get("requestId"),
            "message": "A similar leave request already exists.",
        }

    request_id = f"LR-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    request = {
        "requestId": request_id,
        "empId": empId,
        "fromDate": fromDate,
        "toDate": toDate,
        "reason": reason,
        "status": "pending",
        "appliedAt": datetime.now().isoformat(timespec="seconds"),
    }
    db.leaveRequests.insert_one(request)

    request.pop("_id", None)
    return {
        "success": True,
        "request": request,
        "requestedDays": requested_days,
        "remainingBalanceBeforeRequest": balance["totalRemaining"],
    }


def getCurrentDateTime() -> dict[str, str]:
    """Return the machine's current local date/time for relative dates."""
    return {"currentDateTime": datetime.now().astimezone().isoformat()}


def normalize_month(value: str) -> str:
    """Normalize common month phrases to YYYY-MM."""
    value = value.strip()

    for fmt in ("%Y-%m", "%B %Y", "%b %Y", "%m/%Y"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime("%Y-%m")
        except ValueError:
            pass

    # "March" or "Mar" -> use the current year.
    for fmt in ("%B", "%b"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.replace(year=datetime.now().year).strftime("%Y-%m")
        except ValueError:
            pass

    raise ValueError("Month must look like YYYY-MM, March 2026, or March.")
