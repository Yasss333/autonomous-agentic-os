from uuid import UUID

from fastapi import APIRouter, Depends, Query

from .. import crm_store, deps
from ..deps import CurrentUser, require_password_changed
from ..schemas import (
    ActivityCreate,
    ActivityOut,
    CompanyCreate,
    CompanyOut,
    CompanyUpdate,
    LeadCreate,
    LeadDetail,
    LeadOut,
    LeadUpdate,
    ListResponse,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)

router = APIRouter(prefix="/crm", tags=["crm"], dependencies=[Depends(deps.check_origin)])


def _page(limit: int, offset: int) -> tuple[int, int]:
    return min(max(limit, 1), 100), max(offset, 0)


# ---------- Leads ----------


@router.get("/leads", response_model=ListResponse)
def list_leads(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=200),
    stage: str | None = Query(None),
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(deps.get_conn),
):
    require_password_changed(user)
    limit, offset = _page(limit, offset)
    items, total = crm_store.list_leads(conn, user.workspace_id, limit, offset, search, stage)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/leads", response_model=LeadOut, status_code=201)
def create_lead(
    payload: LeadCreate,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(deps.get_conn),
):
    require_password_changed(user)
    return crm_store.create_lead(conn, user.workspace_id, payload)


@router.get("/leads/{lead_id}", response_model=LeadDetail)
def get_lead(
    lead_id: UUID,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(deps.get_conn),
):
    require_password_changed(user)
    return crm_store.get_lead(conn, user.workspace_id, lead_id)


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(deps.get_conn),
):
    require_password_changed(user)
    return crm_store.update_lead(conn, user.workspace_id, lead_id, payload)


@router.post("/leads/{lead_id}/activities", response_model=ActivityOut, status_code=201)
def add_activity(
    lead_id: UUID,
    payload: ActivityCreate,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(deps.get_conn),
):
    require_password_changed(user)
    return crm_store.add_activity(conn, user.workspace_id, lead_id, payload)


# ---------- Companies ----------


@router.get("/companies", response_model=ListResponse)
def list_companies(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=200),
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(deps.get_conn),
):
    require_password_changed(user)
    limit, offset = _page(limit, offset)
    items, total = crm_store.list_companies(conn, user.workspace_id, limit, offset, search)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/companies", response_model=CompanyOut, status_code=201)
def create_company(
    payload: CompanyCreate,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(deps.get_conn),
):
    require_password_changed(user)
    return crm_store.create_company(conn, user.workspace_id, payload)


@router.patch("/companies/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: UUID,
    payload: CompanyUpdate,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(deps.get_conn),
):
    require_password_changed(user)
    return crm_store.update_company(conn, user.workspace_id, company_id, payload)


# ---------- Tasks ----------


@router.get("/tasks", response_model=ListResponse)
def list_tasks(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    lead_id: UUID | None = Query(None),
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(deps.get_conn),
):
    require_password_changed(user)
    limit, offset = _page(limit, offset)
    items, total = crm_store.list_tasks(conn, user.workspace_id, limit, offset, status, lead_id)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(
    payload: TaskCreate,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(deps.get_conn),
):
    require_password_changed(user)
    return crm_store.create_task(conn, user.workspace_id, payload)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(deps.get_conn),
):
    require_password_changed(user)
    return crm_store.update_task(conn, user.workspace_id, task_id, payload)


# ---------- Search ----------


@router.get("/search")
def search(
    q: str = Query(min_length=1, max_length=200),
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(deps.get_conn),
):
    require_password_changed(user)
    return crm_store.search(conn, user.workspace_id, q)
