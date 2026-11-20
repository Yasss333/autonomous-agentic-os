"""Clarify a bounded CRM feature before requesting code generation."""
import json
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .. import deps
from ..llm import complete_json

router = APIRouter(prefix='/assistant', tags=['assistant'], dependencies=[Depends(deps.check_origin)])


class Message(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=4000)


class Conversation(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=12)


class Plan(BaseModel):
    ready: bool
    reply: str = Field(min_length=1, max_length=2000)
    questions: list[str] = Field(default_factory=list, max_length=3)
    requirement: str = Field(default='', max_length=3200)
    checks: list[str] = Field(default_factory=list, max_length=10)


@router.post('/plan', response_model=Plan)
def plan(payload: Conversation, user=Depends(deps.current_user)):
    deps.require_password_changed(user)
    system = '''You are Zeta, helping a nontechnical person build a feature in a real CRM demo.
Supported: read/filter/score existing leads, companies and tasks; create follow-up tasks,
add activity notes, update lead stages (new/contacted/qualified/customer/lost).
Generated features have a form and a result view; Python runs only in Docker. No email delivery,
external integrations, scheduled jobs, new database fields, or arbitrary new domains in this CRM.
Ask at most 3 short, specific questions if the requested behavior is ambiguous: who is eligible,
what changes, threshold and duplicate behavior. Do not ask again for information already supplied.
If detailed enough, summarize the exact behavior and propose concrete acceptance checks.
Do not claim to have built anything. Unsupported requests must be explained, ready=false.
Return JSON {ready:boolean,reply:string,questions:[string],requirement:string,checks:[string]}.
Requirement must include agreed rules, input defaults and safety/duplicate behavior. It is used by a code generator.
When revising a named tool, require retaining its snake_case name for version history.'''
    try:
        system += '\nUse this exact JSON schema: ' + json.dumps(Plan.model_json_schema())
        system += '\nNever contradict user rules. Questions imply ready=false. If details are supplied, questions=[] and ready=true. Do not invent new required inputs.'
        raw, _, _ = complete_json([{'role': 'system', 'content': system}] + [m.model_dump() for m in payload.messages], max_tokens=2400)
        result = Plan.model_validate_json(raw)
        if result.questions:
            result.ready = False
        if result.ready and (not result.requirement.strip() or not result.checks):
            raise ValueError('Incomplete plan')
        return result
    except (RuntimeError, ValueError):
        raise HTTPException(503, 'Zeta could not prepare a valid plan. Your request is preserved; please retry.') from None
