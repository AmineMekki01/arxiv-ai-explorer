import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt
from src.services import auth as auth_mod


@pytest.mark.unit
class TestAuthService:
    """Tests for src.services.auth helpers."""

    def test_get_password_hash_and_verify(self):
        """Password hashed by get_password_hash should verify with verify_password."""
        password = "super-secret-123"

        hashed = auth_mod.get_password_hash(password)

        assert isinstance(hashed, str)
        assert hashed
        assert auth_mod.verify_password(password, hashed) is True

    def test_verify_password_wrong_password(self):
        """verify_password should return False for incorrect password."""
        password = "correct-password"
        hashed = auth_mod.get_password_hash(password)

        assert auth_mod.verify_password("wrong-password", hashed) is False

    def test_verify_password_handles_bcrypt_error(self, monkeypatch):
        """verify_password should gracefully handle bcrypt.checkpw errors and return False."""

        def boom(_plain: bytes, _hashed: bytes) -> bool:
            raise ValueError("boom")

        monkeypatch.setattr(auth_mod.bcrypt, "checkpw", boom)

        assert auth_mod.verify_password("pw", "hash") is False

    def test_create_and_decode_access_token_default_expiry(self):
        """create_access_token without expires_delta should use default lifetime and be decodable."""
        payload = {"sub": "user-123"}

        token = auth_mod.create_access_token(payload)
        decoded = auth_mod.decode_access_token(token)

        assert decoded is not None
        assert decoded["sub"] == "user-123"
        assert "exp" in decoded

        exp_dt = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        assert exp_dt > datetime.now(timezone.utc)

    def test_create_access_token_with_custom_expiry(self):
        """create_access_token should respect a custom expires_delta."""
        payload = {"sub": "user-123"}
        delta = timedelta(minutes=1)

        token = auth_mod.create_access_token(payload, expires_delta=delta)
        decoded = auth_mod.decode_access_token(token)

        assert decoded is not None
        exp_dt = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert now < exp_dt <= now + timedelta(minutes=2)

    def test_decode_access_token_invalid_signature_returns_none(self):
        """decode_access_token should return None for tokens signed with wrong secret."""
        payload = {"sub": "user-123"}
        wrong_token = jwt.encode(payload, "wrong-secret", algorithm=auth_mod.ALGORITHM)

        assert auth_mod.decode_access_token(wrong_token) is None

    def test_decode_access_token_expired_returns_none(self):
        """decode_access_token should return None for expired tokens."""
        payload = {"sub": "user-123"}
        expired_token = auth_mod.create_access_token(payload, expires_delta=timedelta(minutes=-1))

        assert auth_mod.decode_access_token(expired_token) is None
