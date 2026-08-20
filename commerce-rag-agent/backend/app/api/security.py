import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any

import bcrypt
import jwt
import redis
from fastapi import Header, HTTPException


# ─── JWT 配置（与 Java shopping-platform 共享） ───
JWT_SECRET = os.getenv("JWT_SECRET", "cloudedge-shopping-platform-jwt-secret-2026")
JWT_ALGORITHM = "HS256"

# Redis 配置（用于 JWT 黑名单检查，与 Java 共享同一个 Redis）
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "123456")

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis | None:
    """延迟初始化 Redis 连接（避免启动时连接失败）。"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            _redis_client.ping()
        except Exception:
            _redis_client = None
    return _redis_client


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    username: str = ""
    user_type: int = 1  # 1=C端用户, 2=管理员
    roles: tuple[str, ...] = ("user",)
    auth_source: str = "jwt"

    def has_role(self, *roles: str) -> bool:
        wanted = {role.strip().lower() for role in roles if role.strip()}
        actual = {role.strip().lower() for role in self.roles}
        return bool(wanted & actual)

    @property
    def is_admin(self) -> bool:
        return self.user_type == 2 or self.has_role("admin")


def require_current_user(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    x_user_roles: str | None = Header(default=None),
    x_auth_signature: str | None = Header(default=None),
) -> CurrentUser:
    user = _resolve_current_user(
        authorization=authorization,
        x_user_id=x_user_id,
        x_user_roles=x_user_roles,
        x_auth_signature=x_auth_signature,
        allow_ops_api_key=False,
    )
    if user is None:
        raise HTTPException(status_code=401, detail="login token is required")
    return user


def require_ops_api_key(
    authorization: str | None = Header(default=None),
    x_ops_api_key: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    x_user_roles: str | None = Header(default=None),
    x_auth_signature: str | None = Header(default=None),
) -> CurrentUser:
    expected = os.getenv("OPS_API_KEY", "").strip()
    bearer = _bearer_token(authorization)
    supplied = (x_ops_api_key or bearer or "").strip()
    if expected and supplied and hmac.compare_digest(supplied, expected):
        return CurrentUser(user_id="ops-api-key", roles=("ops",), auth_source="ops_api_key")

    user = _resolve_current_user(
        authorization=authorization,
        x_user_id=x_user_id,
        x_user_roles=x_user_roles,
        x_auth_signature=x_auth_signature,
        allow_ops_api_key=False,
        raise_on_bad_token=False,
    )
    if user and user.has_role("ops", "admin"):
        return user
    raise HTTPException(status_code=403, detail="ops permission is required")


def require_same_user(current_user: CurrentUser, requested_user_id: str | None) -> str:
    if requested_user_id is None or str(requested_user_id).strip() == "":
        return current_user.user_id
    requested = _normalize_user_id(requested_user_id)
    if requested and requested != current_user.user_id:
        raise HTTPException(status_code=403, detail="cannot access another user's data")
    return current_user.user_id


def optional_same_user_filter(current_user: CurrentUser, requested_user_id: str | None) -> str:
    return require_same_user(current_user, requested_user_id)


def _resolve_current_user(
    *,
    authorization: str | None,
    x_user_id: str | None,
    x_user_roles: str | None,
    x_auth_signature: str | None,
    allow_ops_api_key: bool,
    raise_on_bad_token: bool = True,
) -> CurrentUser | None:
    # ─── 优先级 1：Bearer JWT Token（Java 签发） ───
    bearer = _bearer_token(authorization)
    if bearer:
        # 先尝试解析为 Java JWT
        user = _user_from_jwt(bearer)
        if user:
            return user
        # 回退：检查是否是配置的静态 token
        user = _user_from_token(bearer)
        if user:
            return user
        # 回退：检查 ops API key
        expected_ops_key = os.getenv("OPS_API_KEY", "").strip()
        if allow_ops_api_key and expected_ops_key and hmac.compare_digest(bearer, expected_ops_key):
            return CurrentUser(user_id="ops-api-key", roles=("ops",), auth_source="ops_api_key")
        if raise_on_bad_token:
            raise HTTPException(status_code=401, detail="invalid login token")
        return None

    # ─── 优先级 2：可信 Header（网关透传） ───
    if _trusted_auth_header_enabled() and x_user_id:
        if not _trusted_auth_header_signature_valid(x_user_id, x_user_roles, x_auth_signature):
            raise HTTPException(status_code=401, detail="invalid trusted auth header signature")
        return CurrentUser(
            user_id=_normalize_user_id(x_user_id),
            roles=_parse_roles(x_user_roles),
            auth_source="trusted_header",
        )

    # ─── 优先级 3：开发自动登录 ───
    if _dev_auto_login_enabled():
        return CurrentUser(
            user_id=_dev_auto_user_id(),
            username="dev-user",
            roles=_dev_auto_roles(),
            auth_source="dev_auto_login",
        )

    # ─── 优先级 4：开发兜底 ───
    if not _auth_required():
        return CurrentUser(user_id=_dev_user_id(), username="dev-user", roles=("user", "ops"), auth_source="dev_fallback")
    return None


def _user_from_jwt(token: str) -> CurrentUser | None:
    """验证 Java 签发的 JWT Token。"""
    try:
        # 解码并验证签名 + 过期时间
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token has expired")
    except jwt.InvalidTokenError:
        return None

    # 检查 Redis 黑名单（Java 登出时会把 token 加入黑名单）
    r = _get_redis()
    if r is not None:
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            if r.exists(f"security:jwt:blacklist:{token_hash}"):
                raise HTTPException(status_code=401, detail="token has been revoked")
        except HTTPException:
            raise
        except Exception:
            pass  # Redis 不可用时跳过黑名单检查

    # 提取 claims
    user_id = str(payload.get("sub", "")).strip()
    if not user_id:
        return None

    return CurrentUser(
        user_id=user_id,
        username=str(payload.get("username", "")),
        user_type=int(payload.get("userType", 1)),
        roles=_parse_roles(payload.get("roles")),
        auth_source="jwt",
    )


def _user_from_token(token: str) -> CurrentUser | None:
    """回退：检查配置的静态 token 映射。"""
    tokens = _configured_tokens()
    payload = tokens.get(token)
    if payload is None:
        return None
    if isinstance(payload, str):
        return CurrentUser(user_id=_normalize_user_id(payload), roles=("user",), auth_source="token")
    if isinstance(payload, dict):
        user_id = _normalize_user_id(str(payload.get("user_id") or payload.get("sub") or ""))
        if not user_id:
            return None
        return CurrentUser(
            user_id=user_id,
            roles=_parse_roles(payload.get("roles")),
            auth_source="token",
        )
    return None


def _configured_tokens() -> dict[str, Any]:
    raw = os.getenv("APP_USER_TOKENS", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = _parse_compact_tokens(raw)
    return parsed if isinstance(parsed, dict) else {}


def _parse_compact_tokens(raw: str) -> dict[str, Any]:
    tokens: dict[str, Any] = {}
    for item in raw.split(","):
        if not item.strip() or "=" not in item:
            continue
        token, payload = item.split("=", 1)
        parts = payload.split(":")
        tokens[token.strip()] = {
            "user_id": parts[0].strip(),
            "roles": parts[1].split("|") if len(parts) > 1 else ["user"],
        }
    return tokens


def _bearer_token(authorization: str | None) -> str:
    value = (authorization or "").strip()
    if value.lower().startswith("bearer "):
        return value[7:].strip()
    return ""


def _parse_roles(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        roles = [role.strip() for role in value.replace(";", ",").split(",")]
    elif isinstance(value, (list, tuple, set)):
        roles = [str(role).strip() for role in value]
    else:
        roles = ["user"]
    normalized = tuple(dict.fromkeys(role.lower() for role in roles if role))
    return normalized or ("user",)


def _normalize_user_id(value: str) -> str:
    user_id = str(value or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="user id is required")
    if len(user_id) > 64:
        raise HTTPException(status_code=400, detail="user id is too long")
    return user_id


def _auth_required() -> bool:
    return _env_bool("AUTH_REQUIRED", True)


def _trusted_auth_header_enabled() -> bool:
    return _env_bool("TRUSTED_AUTH_HEADER_ENABLED", False)


def _trusted_auth_header_signature_valid(
    user_id: str,
    roles: str | None,
    signature: str | None,
) -> bool:
    if not _trusted_auth_header_signature_required():
        return True
    secret = os.getenv("TRUSTED_AUTH_HEADER_SECRET", "").strip()
    if not secret:
        return False
    supplied = (signature or "").strip()
    if supplied.startswith("sha256="):
        supplied = supplied[7:]
    payload = f"{user_id}\n{roles or ''}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return bool(supplied) and hmac.compare_digest(supplied, expected)


def _trusted_auth_header_signature_required() -> bool:
    return bool(os.getenv("TRUSTED_AUTH_HEADER_SECRET", "").strip()) or _env_bool(
        "TRUSTED_AUTH_HEADER_REQUIRE_SIGNATURE",
        _is_production(),
    )


def _dev_user_id() -> str:
    return os.getenv("DEV_USER_ID", "dev-user").strip() or "dev-user"


def _dev_auto_user_id() -> str:
    return os.getenv("DEV_AUTO_USER_ID", "test-user-001").strip() or "test-user-001"


def _dev_auto_roles() -> tuple[str, ...]:
    return _parse_roles(os.getenv("DEV_AUTO_USER_ROLES", "user,ops"))


def _dev_auto_login_enabled() -> bool:
    return (not _is_production()) and _env_bool("DEV_AUTO_LOGIN_ENABLED", False)


def _is_production() -> bool:
    value = (
        os.getenv("APP_ENV")
        or os.getenv("ENVIRONMENT")
        or os.getenv("FASTAPI_ENV")
        or ""
    ).strip().lower()
    return value in {"prod", "production"}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# ─── 用户认证路由 ───

def create_auth_router():
    """创建用户注册/登录路由（兼容 Java 平台接口格式）。"""
    from fastapi import APIRouter, Request
    from fastapi.responses import JSONResponse
    import jwt as pyjwt

    router = APIRouter(prefix="/api/auth", tags=["auth"])

    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def _verify_password(password: str, stored: str) -> bool:
        # bcrypt 哈希（新用户）；兼容历史 sha256 十六进制哈希（旧用户）
        if stored.startswith("$2"):
            try:
                return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
            except ValueError:
                return False
        return hmac.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), stored)

    def _make_token(user) -> str:
        now = int(time.time())
        payload = {
            "sub": str(user.id),
            "username": user.username,
            "userType": user.user_type,
            "roles": ["admin"] if user.user_type == 2 else ["user"],
            "permissions": [],
            "iat": now,
            "exp": now + 7200,
        }
        return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def _user_info(user) -> dict:
        return {
            "userId": user.id,
            "username": user.username,
            "nickname": user.nickname or user.username,
            "userType": user.user_type,
            "mobile": user.mobile or "",
            "email": user.email or "",
            "avatarUrl": user.avatar_url or "",
            "gender": user.gender,
            "roles": ["admin"] if user.user_type == 2 else ["user"],
            "permissions": [],
        }

    @router.post("/login")
    async def login(request: Request) -> dict:
        from app.models.db import SessionLocal
        from app.models.tables import User
        body = await request.json()
        username = str(body.get("username") or "").strip()
        password = str(body.get("password") or "").strip()
        if not username or not password:
            return JSONResponse(status_code=400, content={"code": "40000", "success": False, "message": "用户名和密码不能为空"})
        with SessionLocal() as db:
            user = db.query(User).filter(User.username == username, User.deleted == 0).first()
            if not user or not _verify_password(password, user.password):
                return JSONResponse(status_code=401, content={"code": "40100", "success": False, "message": "用户名或密码错误"})
            if user.status == 0:
                return JSONResponse(status_code=403, content={"code": "40300", "success": False, "message": "账号已被禁用"})
            # 历史 sha256 哈希自动升级为 bcrypt
            if not user.password.startswith("$2"):
                user.password = _hash_password(password)
                db.commit()
            token = _make_token(user)
            return {"code": "00000", "message": "操作成功", "success": True, "data": {"accessToken": token, "tokenType": "Bearer", "expiresIn": 7200, "userInfo": _user_info(user)}}

    @router.post("/register")
    async def register(request: Request) -> dict:
        from app.models.db import SessionLocal
        from app.models.tables import User
        body = await request.json()
        username = str(body.get("username") or "").strip()
        password = str(body.get("password") or "").strip()
        nickname = str(body.get("nickname") or "").strip()
        if len(username) < 2 or len(username) > 64:
            return JSONResponse(status_code=400, content={"code": "40000", "success": False, "message": "用户名长度 2-64 个字符"})
        if len(password) < 6 or len(password) > 32:
            return JSONResponse(status_code=400, content={"code": "40000", "success": False, "message": "密码长度 6-32 个字符"})
        with SessionLocal() as db:
            if db.query(User).filter(User.username == username).first():
                return JSONResponse(status_code=409, content={"code": "40900", "success": False, "message": "用户名已存在"})
            user = User(username=username, password=_hash_password(password), nickname=nickname or username)
            db.add(user)
            db.commit()
            db.refresh(user)
            token = _make_token(user)
            return {"code": "00000", "message": "注册成功", "success": True, "data": {"accessToken": token, "tokenType": "Bearer", "expiresIn": 7200, "userInfo": _user_info(user)}}

    @router.post("/logout")
    def logout() -> dict:
        return {"code": "00000", "success": True, "message": "操作成功"}

    @router.get("/me")
    def get_me(request: Request) -> dict:
        auth = request.headers.get("Authorization", "")
        user = None
        if auth:
            try:
                user = _user_from_jwt(auth.removeprefix("Bearer ").strip())
            except Exception:
                pass
        if not user:
            return JSONResponse(status_code=401, content={"code": "40100", "success": False, "message": "未登录"})
        from app.models.db import SessionLocal
        from app.models.tables import User as UserModel
        with SessionLocal() as db:
            db_user = db.query(UserModel).filter(UserModel.id == int(user.user_id)).first()
            if not db_user:
                return JSONResponse(status_code=401, content={"code": "40100", "success": False, "message": "用户不存在"})
            return {"code": "00000", "success": True, "data": _user_info(db_user)}

    return router
