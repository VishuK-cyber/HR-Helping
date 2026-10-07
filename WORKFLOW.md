# HR Employee Helpdesk — Workflow

This project intentionally avoids a large agent framework. The agent is just:

**User message → OpenAI model → tool call → Python function → MongoDB → tool result → OpenAI model → final answer**

That makes the flow easy to explain in a viva/demo and easy to debug.

## 1. Data layer

MongoDB contains five collections:

| Collection | Purpose |
|---|---|
| `employees` | Employee identity/basic information |
| `leaves` | Structured leave balances |
| `leaveRequests` | Leave applications written by the agent |
| `payroll` | Monthly salary breakdown |
| `policies` | Human-readable policy text + keywords |

The important design rule is:

- **Numbers/facts** → structured MongoDB collections
- **Rules/text** → `policies` text search

The agent must choose the correct memory source instead of guessing.

## 2. Streamlit layer

`app.py` does only UI work:

1. Loads the `.env` configuration.
2. Lets the user enter/select the logged-in employee ID.
3. Shows the chat.
4. Sends each question to `run_agent()`.
5. Displays the final answer.

It does not contain HR business logic.

## 3. Agent layer

`agent.py` contains:

- The system instructions.
- Five tool definitions.
- The OpenAI Responses API call.
- A small function-calling loop.

The five tools are:

```text
getLeaveBalance(empId)
getPayslip(empId, month)
searchPolicy(keyword)
applyLeave(empId, fromDate, toDate, reason)
getCurrentDateTime()
```

### How the loop works

```text
question
   ↓
model decides whether a tool is needed
   ↓
function_call returned?
   ├─ NO → final answer
   │
   └─ YES
       ↓
   Python runs the requested tool
       ↓
   tool result is sent back to the model
       ↓
   model gives final answer
```

The code allows several tool-call rounds so one question can use more than one tool.

## 4. Tool layer

`tools.py` is where the real rules live.

### `getLeaveBalance`

Reads `leaves` and calculates:

```text
total - used = remaining
```

Example:

```text
sick: 10 total - 3 used = 7 remaining
```

### `getPayslip`

Reads one month from `payroll`.

It also contains the privacy check:

```text
requested empId == logged-in empId ?
            ↓ YES
          return data
            ↓ NO
         deny access
```

This check is in Python, not only in the prompt. That is important because prompts are guidance, while the Python check is an actual application guardrail.

### `searchPolicy`

Searches the `policies` collection using a MongoDB text index and returns at most two matching policies.

A question like:

> Can I carry my leaves forward?

should therefore use `searchPolicy("carry forward leave")`, not `getLeaveBalance()`.

### `applyLeave`

This is the only write tool.

Workflow:

```text
1. Check employee identity
2. Parse dates
3. Calculate inclusive number of days
4. Read current leave balance
5. Refuse if requested days > available days
6. Check for duplicate request
7. Insert into leaveRequests
8. Return request ID
```

For this simple version, the screenshot's tool signature does not include a leave type, so the write tool checks the employee's **combined remaining leave balance**. A production system should add `leaveType` and decrement the correct bucket.

### `getCurrentDateTime`

Used for relative dates such as:

- next Monday
- this month
- tomorrow
- March if the year is omitted

The model should call this tool before resolving dates that depend on the current day/time.

## 5. Privacy behavior

The demo should refuse a question such as:

> What is my colleague's salary?

The model is instructed not to request another employee's payslip, and the Python tool also blocks a payslip request when the requested employee ID is not the logged-in employee ID.

That gives you two layers:

```text
LLM instruction → do not ask for another employee's salary
                      +
Python authorization check → deny even if the model tries
```

## 6. Example end-to-end runs

### A. Leave balance

```text
User:
How many sick leaves do I have left?

Agent:
→ getLeaveBalance(EMP102)
→ MongoDB leaves
→ returns sick = 7
→ final answer: You have 7 sick leaves left.
```

### B. Policy question

```text
User:
Can I carry casual leaves to next year?

Agent:
→ searchPolicy("carry forward casual leave next year")
→ MongoDB policies
→ final answer uses policy text
```

### C. Leave application

```text
User:
I want 3 days of leave from 12 March for a family function.

Agent:
→ getCurrentDateTime() if the year/date needs resolving
→ applyLeave(...)
→ balance check
→ MongoDB insert into leaveRequests
→ final answer includes request status/request ID
```

### D. Privacy

```text
User:
What is my colleague's salary?

Agent:
→ refuse
→ no payslip data is revealed
```

## 7. Why this is intentionally simple

There is no vector database, RAG framework, LangChain graph, Redis layer, or custom memory service here.

For this assignment, those would add moving parts without improving the lesson. MongoDB is already the memory layer, and OpenAI function calling is enough to let the model choose the correct operation.

## 8. Production upgrades later

Once the simple version works, the most useful upgrades would be:

1. Add login/authentication instead of typing an employee ID.
2. Add `leaveType` to `applyLeave`.
3. Use MongoDB transactions for balance updates + leave requests.
4. Add an approval workflow for managers.
5. Add audit logging for every tool call.
6. Add unit tests for each tool before changing the agent layer.
