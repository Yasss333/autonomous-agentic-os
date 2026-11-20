import json
import time
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from api import config, deps
from api.main import app


class ClerkAuthTest(unittest.TestCase):
    issuer = "https://clerk.example.test"
    origin = "http://localhost:5173"

    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.key.public_key()))
        cls.jwks = {"keys": [{**jwk, "kid": "test", "alg": "RS256", "use": "sig"}]}

    def setUp(self):
        self.conn = MagicMock()
        self.cur = self.conn.cursor.return_value.__enter__.return_value
        self.user_id = uuid4()
        self.cur.fetchone.return_value = {
            "id": self.user_id, "email": "reviewer@example.test", "workspace_id": uuid4(),
            "workspace_slug": "demo", "must_change_password": False, "sponsored_task_used": True,
        }
        self.client = self.enterContext(TestClient(app))
        self.enterContext(patch.dict(app.dependency_overrides, {deps.get_conn: lambda: self.conn}))
        self.enterContext(patch.multiple(config, CLERK_ISSUER=self.issuer,
                                         CLERK_AUTHORIZED_PARTIES={self.origin}))
        self.enterContext(patch.object(jwt.PyJWKClient, "fetch_data", return_value=self.jwks))

    def token(self, signing_key=None, **claims):
        now = int(time.time())
        return jwt.encode(
            {"iss": self.issuer, "azp": self.origin, "sub": "user_reviewer", "sid": "sess_test",
             "exp": now + 60, "nbf": now - 1, "iat": now, **claims},
            signing_key or self.key, algorithm="RS256", headers={"kid": "test"},
        )

    def me(self, token):
        return self.client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    def test_valid_jwt_uses_existing_workspace_user(self):
        response = self.me(self.token())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(self.user_id))
        self.assertTrue(response.json()["sponsored_task_used"])
        self.assertEqual(self.cur.execute.call_args.args[1], ("user_reviewer",))

    def test_invalid_tokens_never_lookup_users(self):
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        for token in [
            "invalid", self.token(signing_key=other_key), self.token(exp=int(time.time()) - 11),
            self.token(nbf=int(time.time()) + 60), self.token(azp="https://wrong.example.test"),
            self.token(iss="https://wrong.clerk.example.test"), self.token(sts="pending"),
        ]:
            with self.subTest(case=token[:20]):
                self.assertEqual(self.me(token).status_code, 401)
        self.cur.execute.assert_not_called()

    def test_unlinked_or_disabled_user_is_forbidden(self):
        self.cur.fetchone.return_value = None
        self.assertEqual(self.me(self.token()).status_code, 403)

    def test_legacy_cookie_and_password_login_cannot_bypass_clerk(self):
        self.client.cookies.set("aos_session", "old-cookie")
        self.assertEqual(self.client.get("/api/me").status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json={
            "email": "reviewer@example.test", "password": "old-password",
        }).status_code, 404)
        self.cur.execute.assert_not_called()

    def test_small_clock_skew_is_accepted(self):
        now = int(time.time())
        self.assertEqual(self.me(self.token(iat=now + 7, nbf=now + 7)).status_code, 200)
        self.assertEqual(self.me(self.token(iat=now + 60)).status_code, 401)
