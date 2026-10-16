# HR Helpdesk Workflow

## Start and menu

Run python terminal_agent.py and enter an operator label for the local audit log. The label is self-reported; this demo does not authenticate the operator.

1. Ask a natural-language HR question.
2. Search employees by employee ID or name.
3. View an employee profile.
4. Update a basic profile field.
5. View employee change history.
6. Exit.

## Natural-language questions

1. Send the HR request text to OpenAI for intent and field extraction. Do not send employee documents, database results, or conversation history.
2. If OpenAI is unavailable, its key is missing, or its response cannot be parsed, try Gemini with the same request text.
3. Validate the returned action, employee query, and field against the fixed allow-lists in code.
4. Fetch employee facts from MongoDB locally. If a name matches multiple employees, ask the operator to choose an employee ID.
5. Format answers from MongoDB values in the terminal. The model does not supply employee facts.
6. If both providers fail, show a safe message and keep direct search, view, update, and history options available.

The natural-language path supports employee search, profile viewing, questions about employee fields, roster lists, change-history lookup, and proposed updates to approved fields. Natural-language updates are interpreted by the model, then previewed and explicitly confirmed in the local terminal before being saved.

## Data access

The assistant reads the employees collection and displays only:

- empId
- name
- department
- designation (shown as job title)
- workEmail
- phone
- managerId
- joiningDate

Search uses employee ID or employee name. Direct lookups accept the full ID (EMP102) or numeric part (102), and normalize IDs to uppercase.

## Allowed updates

| HR label | MongoDB field | Validation |
| --- | --- | --- |
| Department | department | Required single-line text, up to 120 characters |
| Job title | designation | Required single-line text, up to 120 characters |
| Work email | workEmail | Basic email format |
| Phone | phone | 7 to 15 digits; common separators are accepted |
| Manager employee ID | managerId | Must identify another existing employee; enter the full ID or numeric part, or enter none to clear |

The employee ID, name, joining date, payroll, and leave records cannot be changed through this workflow. The terminal flow does not add or delete employee records.

For every update, load and validate the current record, show the employee and old/new field values, then require the exact input YES. Cancel for any other input. Recheck the old value immediately before writing. Save the profile update and its audit record in one MongoDB transaction.

## Audit history

Each successful change adds a document to employeeChangeLog with the change ID, employee ID and name, field, old and new values, operator label, and UTC timestamp. The history option shows up to 20 recent changes for the selected employee.

## Provider and data boundary

The operator's natural-language request text is sent to Gemini, then OpenAI if needed. It may include the employee name or ID typed by the operator. MongoDB results are never sent to either provider. HR reads can display every field stored on employee documents; writes are limited to department, job title, work email, phone, manager employee ID, and salary. Natural-language changes use the same local preview, explicit YES confirmation, and audit log as menu changes.

This is for local testing only, not real employee records. Add verified HR authentication and authorization before any workplace use.

## Error behavior

Database operations return structured results and user-facing messages do not include credentials or raw exceptions. If the database does not support transactions, profile updates fail. Provider errors do not prevent direct menu operations.
