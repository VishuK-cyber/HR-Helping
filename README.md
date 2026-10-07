# HR Employee Helpdesk

A deliberately small Python + Streamlit HR agent using MongoDB and OpenAI function calling.

## What it does

- Exact leave balance from `leaves`
- Exact payslip from `payroll`
- Policy answers from `policies`
- Leave application into `leaveRequests`
- Current date/time for relative dates
- Privacy guardrail so the logged-in employee cannot retrieve another employee's payslip

## Project structure

```text
hr_employee_helpdesk/
├── app.py              # Streamlit UI
├── agent.py            # LLM + tool-calling loop
├── tools.py            # HR tools / business rules
├── db.py               # MongoDB connection + text index
├── config.py           # .env loading
├── seed_db.py          # Optional demo data
├── WORKFLOW.md         # Architecture and step-by-step workflow
├── requirements.txt
├── .env.example
└── .gitignore
```

## 1. Create/activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 2. Install packages

```powershell
pip install -r requirements.txt
```

## 3. Add your existing `.env`

The app expects:

```env
OPENAI_API_KEY=...
MONGODB_URI=...
MONGODB_DB=hr_helpdesk
OPENAI_MODEL=gpt-5.5
```

You can omit the last two because the code has defaults.

## 4. Optional: seed the demo database

Only run this if you want the sample employee/data shown in the assignment:

```powershell
python seed_db.py
```

It creates demo data for `EMP102` and a few policy documents.

## 5. Run Streamlit

```powershell
streamlit run app.py
```

Then open the local URL Streamlit prints in the terminal.

## Demo questions

```text
How many sick leaves do I have left? I am EMP102.
What does the policy say about working from home?
What was my March salary?
I want three days of leave from 12 March for a family function.
I have two casual leaves left - does the policy let me carry them to next year?
What is my colleague's salary?
```

The last question should be refused.
