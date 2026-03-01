"""Shared test fixtures and mocks for the cont-synth test suite.

IMPORTANT: Heavy dependencies are mocked here BEFORE any project code is
imported. conftest.py is loaded by pytest before test collection, so
sys.modules mutations take effect globally.
"""
import os
import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Mock google.generativeai before any project imports.
# Prevents API initialisation failures when no key is configured.
# ---------------------------------------------------------------------------
_genai_mock = MagicMock()
_genai_mock.GenerativeModel.return_value = MagicMock()

if "google" not in sys.modules:
    _google_mock = MagicMock()
    _google_mock.generativeai = _genai_mock
    sys.modules["google"] = _google_mock

sys.modules["google.generativeai"] = _genai_mock

# Provide a dummy API key so genai.configure() doesn't raise
os.environ.setdefault("GEMINI_API_KEY", "test-api-key-for-unit-tests")

# ---------------------------------------------------------------------------
# Mock optional document-parsing libraries that may not be installed
# ---------------------------------------------------------------------------
if "PyPDF2" not in sys.modules:
    sys.modules["PyPDF2"] = MagicMock()
if "docx" not in sys.modules:
    sys.modules["docx"] = MagicMock()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
import pytest
from sqlmodel import SQLModel, create_engine, Session


@pytest.fixture(scope="function")
def db_session():
    """Provide a fresh in-memory SQLite session for each test.

    All models are imported here (after mocks are in place) so their
    SQLModel metadata gets registered before create_all() is called.
    """
    # Import models to register their metadata
    from cont_synth.models import (  # noqa: F401
        Product,
        Persona,
        Interview,
        Opportunity,
        InterviewOpportunityLink,
        Outcome,
        OutcomeOpportunityLink,
        Solution,
        Experiment,
        User,
        LlmUsageLog,
    )
    from cont_synth.state.core import PersonaPrep  # noqa: F401

    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    engine.dispose()
