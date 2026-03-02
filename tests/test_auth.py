"""Unit tests for password-hashing authentication helpers."""
import pytest

from cont_synth.state.auth import _hash_password, _verify_password


class TestHashPassword:
    def test_returns_string(self):
        result = _hash_password("password123")
        assert isinstance(result, str)

    def test_not_plaintext(self):
        password = "supersecret"
        hashed = _hash_password(password)
        assert hashed != password

    def test_bcrypt_prefix(self):
        hashed = _hash_password("any_password")
        # bcrypt hashes start with $2b$ or $2a$
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_unique_salts(self):
        """Same password produces different hash each time due to random salt."""
        password = "samepassword"
        hash1 = _hash_password(password)
        hash2 = _hash_password(password)
        assert hash1 != hash2

    def test_hash_has_reasonable_length(self):
        hashed = _hash_password("test")
        # bcrypt hashes are 60 characters
        assert len(hashed) == 60

    def test_empty_password(self):
        result = _hash_password("")
        assert isinstance(result, str)
        assert len(result) == 60


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        password = "mypassword"
        hashed = _hash_password(password)
        assert _verify_password(password, hashed) is True

    def test_wrong_password_returns_false(self):
        hashed = _hash_password("correctpassword")
        assert _verify_password("wrongpassword", hashed) is False

    def test_case_sensitive_lower(self):
        hashed = _hash_password("Password")
        assert _verify_password("password", hashed) is False

    def test_case_sensitive_upper(self):
        hashed = _hash_password("Password")
        assert _verify_password("PASSWORD", hashed) is False

    def test_exact_match(self):
        hashed = _hash_password("Password")
        assert _verify_password("Password", hashed) is True

    def test_empty_password_round_trip(self):
        hashed = _hash_password("")
        assert _verify_password("", hashed) is True
        assert _verify_password("notempty", hashed) is False

    def test_special_characters(self):
        password = "p@$$w0rd!#%^&*()"
        hashed = _hash_password(password)
        assert _verify_password(password, hashed) is True
        assert _verify_password("p@$$w0rd", hashed) is False

    def test_unicode_password(self):
        password = "contraseña_123"
        hashed = _hash_password(password)
        assert _verify_password(password, hashed) is True
        assert _verify_password("contrasena_123", hashed) is False

    def test_long_password(self):
        password = "A" * 72  # bcrypt max effective length
        hashed = _hash_password(password)
        assert _verify_password(password, hashed) is True

    def test_multiple_hashes_all_verify(self):
        """All hashes of the same password should verify correctly."""
        password = "multitest"
        hashes = [_hash_password(password) for _ in range(3)]
        for h in hashes:
            assert _verify_password(password, h) is True
