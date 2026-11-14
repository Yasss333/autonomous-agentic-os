from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

LeadStage = Literal["new", "contacted", "qualified", "customer", "lost"]
TaskStatus = Literal["open", "done", "cancelled"]
ActivityKind = Literal["note", "call", "email", "meeting"]
EntityType = Literal["lead", "company", "activity", "task"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=10, max_length=256)


class MeResponse(BaseModel):
    id: UUID
    email: str
    workspace_id: UUID
    workspace_slug: str
    must_change_password: bool
    sponsored_task_used: bool


class NodeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: EntityType
    name: str
    version: int
    created_at: datetime
    updated_at: datetime


class LeadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    company_id: UUID | None = None
    stage: LeadStage = "new"
    last_contact_date: date | None = None
    value: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class LeadUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    company_id: UUID | None = None
    stage: LeadStage | None = None
    last_contact_date: date | None = None
    value: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    version: int = Field(ge=1)


class LeadOut(NodeBase):
    email: str
    company_id: UUID | None
    company_name: str | None = None
    stage: LeadStage
    last_contact_date: date | None
    value: Decimal | None
    currency: str


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    website: str | None = Field(default=None, max_length=300)
    industry: str | None = Field(default=None, max_length=120)


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    website: str | None = Field(default=None, max_length=300)
    industry: str | None = Field(default=None, max_length=120)
    version: int = Field(ge=1)


class CompanyOut(NodeBase):
    website: str | None
    industry: str | None


class ActivityCreate(BaseModel):
    kind: ActivityKind = "note"
    body: str = Field(min_length=1, max_length=4000)
    occurred_at: datetime | None = None


class ActivityOut(NodeBase):
    kind: ActivityKind
    body: str
    occurred_at: datetime
    lead_id: UUID


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    due_date: date
    lead_id: UUID | None = None
    status: TaskStatus = "open"


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    due_date: date | None = None
    status: TaskStatus | None = None
    version: int = Field(ge=1)


class TaskOut(NodeBase):
    title: str
    due_date: date
    status: TaskStatus
    lead_id: UUID | None = None


class LeadDetail(LeadOut):
    activities: list[ActivityOut] = []
    tasks: list[TaskOut] = []


class ListResponse(BaseModel):
    items: list
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
