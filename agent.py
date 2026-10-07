from __future__ import annotations

import json
from typing import Any, Callable

from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL
from tools import (
    applyLeave,
    getCurrentDateTime,
    getLeaveBalance,
    getPayslip,
    searchPolicy,
)

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
You are a simple internal HR Employee Helpdesk agent.

Your job is to answer employee questions using the available tools. Do not invent
leave balances, salary numbers, policy text, dates, request IDs, or employee data.

RULES:
1. Structured facts come from tools:
   - leave balance -> getLeaveBalance
   - payslip/salary -> getPayslip
   - company policy -> searchPolicy
2. Policy questions must use searchPolicy. Never answer policy questions from the
   leave balance or payroll data.
3. Leave applications must use applyLeave. It is a WRITE operation. Never say a
   leave was submitted unless the tool returns success=true.
4. Before relative-date work such as "next Monday" or "this month", call
   getCurrentDateTime(). Use the result to resolve the date.
5. You are operating for the logged-in employee only. The employee ID supplied by
   the application is the only employee you may access.
6. Never retrieve or reveal a colleague's payslip/salary. Refuse the request
   politely without trying to bypass the privacy rule.
7. Keep answers concise and practical. Mention the relevant numbers or policy text.
8. If a tool returns an error, explain the error plainly and do not pretend the
   operation succeeded.

Current logged-in employee ID: {emp_id}
"""


def tool_schema(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
        "strict": True,
    }


TOOLS = [
    tool_schema(
        "getLeaveBalance",
        "Get remaining leave balances by type. Use for exact leave numbers.",
        {"empId": {"type": "string"}},
        ["empId"],
    ),
    tool_schema(
        "getPayslip",
        "Get the logged-in employee's payslip for a month. Never use for another employee.",
        {
            "empId": {"type": "string"},
            "month": {"type": "string", "description": "YYYY-MM, e.g. 2026-03, or March 2026"},
        },
        ["empId", "month"],
    ),
    tool_schema(
        "searchPolicy",
        "Search company policy text. Return at most two matching policy entries.",
        {"keyword": {"type": "string"}},
        ["keyword"],
    ),
    tool_schema(
        "applyLeave",
        "Create a leave request after checking available balance. Dates must be YYYY-MM-DD.",
        {
            "empId": {"type": "string"},
            "fromDate": {"type": "string"},
            "toDate": {"type": "string"},
            "reason": {"type": "string"},
        },
        ["empId", "fromDate", "toDate", "reason"],
    ),
    tool_schema(
        "getCurrentDateTime",
        "Get current local date/time for resolving relative dates.",
        {},
        [],
    ),
]


def run_tool(name: str, args: dict[str, Any], emp_id: str) -> dict[str, Any]:
    """One small dispatcher keeps the agent code easy to understand."""
    if name == "getLeaveBalance":
        return getLeaveBalance(args["empId"])
    if name == "getPayslip":
        return getPayslip(args["empId"], args["month"], emp_id)
    if name == "searchPolicy":
        return searchPolicy(args["keyword"])
    if name == "applyLeave":
        return applyLeave(
            args["empId"], args["fromDate"], args["toDate"], args["reason"], emp_id
        )
    if name == "getCurrentDateTime":
        return getCurrentDateTime()

    raise ValueError(f"Unknown tool: {name}")


def run_agent(user_message: str, emp_id: str) -> str:
    """Run one agent turn, including any function-call/tool-call loop."""
    instructions = SYSTEM_PROMPT.format(emp_id=emp_id)

    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=instructions,
        input=user_message,
        tools=TOOLS,
        max_output_tokens=600,
    )

    # The Responses API can return function-call items. We execute them locally,
    # feed their results back, and ask the model to finish the answer.
    for _ in range(6):
        tool_outputs = []

        for item in response.output:
            if item.type != "function_call":
                continue

            args = json.loads(item.arguments)
            result = run_tool(item.name, args, emp_id)
            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(result, default=str),
                }
            )

        if not tool_outputs:
            return response.output_text or "I could not produce an answer."

        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions=instructions,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=TOOLS,
            max_output_tokens=600,
        )

    return "I stopped after too many tool calls. Please try the request again."
