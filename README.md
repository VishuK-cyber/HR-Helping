# HR Helpdesk

A terminal assistant for local HR testing. It supports natural-language employee questions through Gemini, with OpenAI as a fallback, and reads factual employee data directly from MongoDB.

## First-version scope

- Search employees by employee ID or name.
- View all fields stored on employee records, including salary if present.
- Update department, job title, work email, phone, manager employee ID, or salary.
- Review the before and after values and type YES before each save.
- Record every saved change in the employeeChangeLog collection.
- View an employee's recent change history.

Only the listed profile fields can be updated; other fields are read-only. It does not add or delete employee records. Natural-language requests are interpreted by Gemini first and OpenAI if Gemini fails. The models receive the request text, not employee records returned by MongoDB. Keep sensitive details out of the request text; the direct menu options still work if both providers are unavailable.

## Run it

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt

Create .env from .env.example and configure MONGODB_URI and at least one AI key. Set OPENAI_API_KEY for the primary provider and GEMINI_API_KEY to enable fallback. MONGODB_DB_NAME defaults to hr_helpdesk; model names can be changed with OPENAI_MODEL and GEMINI_MODEL. Then run:

    python terminal_agent.py

The database must already contain an employees collection with empId values. The current profile shape uses name, department, designation, managerId, and joiningDate; this assistant also reads or writes workEmail and phone. Employee IDs are the stable record keys; enter either EMP102 or its numeric part, 102. Updating a manager requires an existing employee ID or the value none.

The assistant creates employeeChangeLog if needed. Profile updates and their audit entries are written in one MongoDB transaction. The configured MongoDB deployment must support transactions.

When the program starts, choose 1 to ask a natural-language question, 2 to search, 3 to view a profile, 4 to update a profile field, or 5 to view change history. Direct lookup accepts EMP102 or 102.

## Access boundary

This is a local terminal demo and does not authenticate the operator. The operator name entered at startup is self-reported and used only as the audit actor. Natural-language request text is sent to OpenAI, then Gemini if needed; database results stay local. Do not use this version with real employee data.
