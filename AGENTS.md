# HR Helpdesk Project Guidance

## Current design

This is a small local terminal MVP for HR staff to search, view, and maintain employee data in MongoDB. Gemini interprets natural-language questions first and OpenAI is the fallback; providers receive only the request text, never database results. Employee facts are read and formatted locally.

- Search by employee ID or name; open a record by employee ID.
- View all fields present on employee documents, including fields such as salary when present.
- Update department, job title, work email, phone, manager employee ID, or salary.
- Show old and proposed values and require the exact confirmation YES before a write.
- Write the profile change and audit entry atomically to employees and employeeChangeLog.
- View recent change history for an employee.
- Only department, job title, work email, phone, manager employee ID, and salary can be updated. Other fields remain read-only. No employee creation or deletion.

The operator name is self-reported for audit attribution. This terminal MVP has no authentication and is for trusted local testing only, not real employee data.

## Working rules

1. Before a multi-step project change, present a written plan and wait for the user's approval.
2. Never hardcode secrets or print credentials. Use environment variables and do not read or expose .env values.
3. Enforce update restrictions in code. Do not rely on conversational instructions alone.
4. Require a fresh before/after preview and explicit YES before each employee profile write.
5. Keep audit logging in the same transaction as the employee update.
6. Do not change employee schema or database operations without explicit user approval. The basic HR profile update scope and employeeChangeLog collection were approved on 2026-10-16.
7. Preserve unrelated user changes. Do not restore files that are already deleted in the working tree unless the user asks.
8. Keep changes small; do not add dependencies without telling the user first.
9. Return structured results from database operations and do not show raw database exceptions.
10. At the end of each task, update Current Status and the Decision Log.

## Current status

- [x] Terminal HR lookup for employee ID or name.
- [x] Basic employee profile view.
- [x] Confirmed updates to the approved profile fields with an audit entry.
- [x] OpenAI natural-language interpretation with Gemini fallback.
- [x] Local employee history view; provider requests contain no database results.
- [ ] Verified HR sign-in and authorization before workplace deployment.
- [ ] Live MongoDB transaction and data validation.
- Automated tests and live provider/database checks were not run for this task.

The pre-existing working tree had deletions for app/__init__.py, app/db.py, app/tools.py, scripts/seed_db.py, scripts/verify_db.py, tests/test_db.py, and tests/test_tools.py. Those deletions were preserved. The current runtime uses terminal_agent.py and hr_records.py.

## Project files

- terminal_agent.py: terminal menu, natural-language routing, and confirmation flow.
- hr_ai.py: OpenAI-first request interpretation with Gemini fallback.
- hr_records.py: employee search, read, validation, update, and audit operations.
- README.md: setup and first-version scope.
- WORKFLOW.md: runtime workflow, field rules, and access boundary.
- .env.example: MongoDB and AI provider configuration names.

The runtime expects an existing employees collection. Existing fields include empId, name, department, designation, managerId, and joiningDate. The approved profile workflow also uses workEmail and phone. Audit entries are stored in employeeChangeLog.

## Current Status and Decision Log

- **2026-10-16**: Replaced the single-employee self-service workflow with an HR terminal MVP for employee lookup and basic profile maintenance. Allowed updates are department, designation, workEmail, phone, and managerId. Each update requires explicit confirmation and writes an audit entry in the same MongoDB transaction.
- **2026-10-16**: Restored OpenAI-first natural-language interpretation with Gemini fallback. Provider requests contain the HR question only; employee records remain in MongoDB and are formatted locally.
- **2026-10-16**: Added read-only employee change history. Profile writes still use the local confirmed workflow.
- **2026-10-16**: The user confirmed this is for local testing only, not real employee data.
- **2026-10-16**: Kept the existing working-tree deletions and untracked interview guide files unchanged.
- **2026-10-16**: No authentication is implemented. The terminal workflow is local-demo only until verified HR sign-in and authorization are added.
