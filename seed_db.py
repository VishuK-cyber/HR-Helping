from db import get_db


db = get_db()

# Demo employee.
db.employees.update_one(
    {"empId": "EMP102"},
    {
        "$set": {
            "empId": "EMP102",
            "name": "Demo Employee",
            "department": "Engineering",
            "designation": "Software Trainee",
            "joiningDate": "2025-08-01",
            "managerId": "MGR001",
        }
    },
    upsert=True,
)

# Leave balances.
for doc in [
    {"empId": "EMP102", "type": "casual", "total": 12, "used": 5},
    {"empId": "EMP102", "type": "sick", "total": 10, "used": 3},
    {"empId": "EMP102", "type": "earned", "total": 18, "used": 8},
]:
    db.leaves.update_one(
        {"empId": doc["empId"], "type": doc["type"]}, {"$set": doc}, upsert=True
    )

# Demo March payslip.
db.payroll.update_one(
    {"empId": "EMP102", "month": "2026-03"},
    {
        "$set": {
            "empId": "EMP102",
            "month": "2026-03",
            "basic": 30000,
            "hra": 12000,
            "deductions": 3500,
            "netPay": 38500,
        }
    },
    upsert=True,
)

# Policy examples used by the demo questions.
policies = [
    {
        "policyId": "P001",
        "title": "Work From Home",
        "category": "attendance",
        "content": "Employees may work from home up to two days per week with manager approval.",
        "keywords": ["work from home", "wfh", "remote", "attendance"],
    },
    {
        "policyId": "P002",
        "title": "Leave Carry Forward",
        "category": "leave",
        "content": "Up to 5 unused earned leaves may be carried forward to the next calendar year. Casual and sick leaves cannot be carried forward.",
        "keywords": ["carry forward", "carry over", "leave", "next year"],
    },
    {
        "policyId": "P003",
        "title": "Notice Period",
        "category": "separation",
        "content": "The standard notice period for permanent employees is 30 days unless the employment contract states otherwise.",
        "keywords": ["notice period", "resignation", "notice"],
    },
]

for policy in policies:
    db.policies.update_one(
        {"policyId": policy["policyId"]}, {"$set": policy}, upsert=True
    )

print("Demo HR data is ready in database:", db.name)
print("Try employee ID: EMP102")
