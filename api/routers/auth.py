from fastapi import APIRouter, Depends, HTTPException, Request, Response
from psycopg.rows import dict_row

from .. import config, deps, security
from ..deps import CurrentUser, check_login_throttle, clear_login_failures, get_conn, record_login_failure
from ..schemas import ChangePasswordRequest, LoginRequest, MeResponse

def require_legacy_auth():
    if config.CLERK_ISSUER:
        raise HTTPException(404, "Use Clerk to manage your session")


router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(require_legacy_auth)])


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    conn=Depends(get_conn),
):
    deps.check_origin(request)
    check_login_throttle(request, payload.email)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT id, email, password_hash, workspace_id, must_change_password, status
               FROM users WHERE lower(email) = lower(%s)""",
            (payload.email,),
        )
        user = cur.fetchone()
        ok = bool(
            user
            and user["status"] == "active"
            and security.verify_password(user["password_hash"], payload.password)
        )
        if not ok:
            record_login_failure(request, payload.email)
            raise HTTPException(401, "Invalid email or password")
        clear_login_failures(request, payload.email)

        token, token_hash = security.new_session_token()
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent", "")[:300]
        cur.execute(
            """INSERT INTO sessions (user_id, token_hash, expires_at, ip, user_agent)
               VALUES (%s, %s, %s, %s, %s)""",
            (user["id"], token_hash, security.session_expiry(), ip, ua),
        )
    response.set_cookie(value=token, **security.cookie_kwargs())
    return {"status": "ok", "must_change_password": user["must_change_password"]}


@router.post("/logout")
def logout(request: Request, response: Response, conn=Depends(get_conn)):
    deps.check_origin(request)
    token = request.cookies.get(security.SESSION_COOKIE)
    if token:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET revoked_at = now() WHERE token_hash = %s AND revoked_at IS NULL",
                (security.token_digest(token),),
            )
    response.delete_cookie(security.SESSION_COOKIE, path="/")
    return {"status": "ok"}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(get_conn),
):
    deps.check_origin(request)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT password_hash FROM users WHERE id = %s", (user.id,))
        row = cur.fetchone()
        if not row or not security.verify_password(row["password_hash"], payload.current_password):
            raise HTTPException(400, "Current password is incorrect")
        cur.execute(
            """UPDATE users SET password_hash = %s, must_change_password = false
               WHERE id = %s""",
            (security.hash_password(payload.new_password), user.id),
        )
        # Revoke other sessions; keep the current one.
        cur.execute(
            """UPDATE sessions SET revoked_at = now()
               WHERE user_id = %s AND revoked_at IS NULL
                 AND token_hash <> %s""",
            (user.id, security.token_digest(request.cookies.get(security.SESSION_COOKIE, ""))),
        )
    return {"status": "ok"}
