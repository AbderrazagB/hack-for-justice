"""The API we would sell.

Its contract is the product, so these assert the boundaries a buyer's security
review would ask about -- authentication, tenancy, quota -- and the shape of
the response they would code against.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import BytesIO
from unittest.mock import patch

import pytest
from PIL import Image

from app.core.api_auth import current_api_caller
from app.main import app
from app.models.api_key import (
    ApiKey,
    generate_key,
    hash_key,
    roll_period_if_due,
)
from app.services.ocr_service import OCRResult, OCRService
from tests.conftest import document_text

TXN = "RNE_MODIFICATION_ENTREPRISE"


def _png() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (60, 30), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def _fake_extract(self, content, filename="", document_type="general", force_local=False):
    fields = {
        "id_new_representative": {"id_number": "12345678", "person_name": "Amine Ben Salah"},
        "general_assembly_pv": {"id_number": "87654321", "person_name": "Amine Ben Salah"},
    }.get(document_type, {})
    return OCRResult(
        document_type=document_type,
        fields=dict(fields),
        full_text=document_text(document_type),
        engine="test",
    )


def _stub_key(**overrides) -> ApiKey:
    """A key that never touches the database."""
    _, hashed, prefix = generate_key()
    defaults = {
        "name": "Test",
        "owner": "buyer@example.tn",
        "key_hash": hashed,
        "key_prefix": prefix,
        "monthly_quota": 1000,
        "calls_this_period": 0,
        "period_started_at": datetime.now(UTC),
    }
    return ApiKey(**{**defaults, **overrides})


class _Caller:
    """Stands in for the dependency, counting calls the way the real one does."""

    def __init__(self, key: ApiKey):
        self.key = key

    @property
    def owner(self) -> str:
        return self.key.owner

    @property
    def remaining(self) -> int:
        return max(0, self.key.monthly_quota - self.key.calls_this_period)

    async def record_call(self) -> None:
        self.key.calls_this_period += 1


def _as(key: ApiKey) -> None:
    app.dependency_overrides[current_api_caller] = lambda: _Caller(key)


def _validate(client, *, doc_types=("id_new_representative", "general_assembly_pv"), **extra):
    files = [("files", (f"{d}.png", _png(), "image/png")) for d in doc_types]
    data = {"transaction_type": TXN, "document_types": list(doc_types), **extra}
    with patch.object(OCRService, "extract", _fake_extract):
        return client.post("/v1/validate", files=files, data=data)


# ---------------------------------------------------------- authentication

def test_every_endpoint_refuses_an_unauthenticated_caller(anon_client) -> None:
    """The whole surface is behind a key, not just the expensive part."""
    for method, path in (
        ("get", "/v1/transactions"),
        ("get", "/v1/usage"),
        ("get", "/v1/validations/anything"),
        ("post", "/v1/validate"),
    ):
        assert getattr(anon_client, method)(path).status_code == 401, path


def test_a_key_is_looked_up_by_hash_not_stored_in_plain_text() -> None:
    full, hashed, prefix = generate_key()
    assert full.startswith("sk_sahilli_")
    assert hashed == hash_key(full)
    assert hashed != full
    # The displayable part identifies the key without revealing it.
    assert full.startswith(prefix) and len(prefix) < len(full)


def test_a_revoked_key_is_not_active() -> None:
    key = _stub_key(revoked_at=datetime.now(UTC))
    assert key.active is False


def test_the_public_view_of_a_key_carries_no_secret() -> None:
    key = _stub_key()
    public = key.to_public()
    assert "key_hash" not in public
    assert not any("sk_sahilli_" in str(v) and len(str(v)) > 30 for v in public.values())


# ------------------------------------------------------------------ catalogue

def test_transactions_lists_what_can_be_validated(client) -> None:
    _as(_stub_key())
    body = client.get("/v1/transactions").json()

    entry = next(t for t in body if t["transaction_type"] == TXN)
    assert entry["official_reference"] == "RNE-M-005"
    assert len(entry["required_documents"]) == 5
    # The keys an integrator must send back.
    assert all(d["key"] and d["label_fr"] for d in entry["required_documents"])


# ------------------------------------------------------------------ validate

def test_validate_answers_with_the_verdict_and_the_findings(client) -> None:
    _as(_stub_key())
    body = _validate(client).json()

    assert body["accepted"] is False
    assert body["status"] in {"INCOMPLETE", "NEEDS_REVIEW"}
    assert body["validation_id"]
    assert any(f["code"] == "id_number_matches_across_documents" for f in body["findings"])
    # Rules that did not run are named, not omitted.
    assert any(s["name"] == "declaration_matches_documents" for s in body["skipped_checks"])


def test_accepted_is_true_only_when_nothing_is_wrong(client) -> None:
    """The single field an integrator branches on."""
    _as(_stub_key())

    def clean(self, content, filename="", document_type="general", force_local=False):
        return OCRResult(
            document_type=document_type,
            fields={
                "id_number": "12345678",
                "person_name": "Amine Ben Salah",
                "issue_date": "2026-06-01",
                "decision_date": "2026-06-12",
                "signature_date": "2026-06-12",
                "has_signature": True,
                "full_text": "Gérant: Amine Ben Salah",
            },
            full_text=document_text(document_type),
            engine="test",
        )

    doc_types = (
        "id_new_representative",
        "company_statutes",
        "rne_extract",
        "tax_registration_card",
        "general_assembly_pv",
    )
    files = [("files", (f"{d}.png", _png(), "image/png")) for d in doc_types]
    with patch.object(OCRService, "extract", clean):
        body = client.post(
            "/v1/validate",
            files=files,
            data={
                "transaction_type": TXN,
                "document_types": list(doc_types),
                "submitted_at": "2026-07-01",
            },
        ).json()

    assert body["accepted"] is True
    assert body["status"] == "COMPLETE"
    assert body["summary"]["total"] == 0


def test_an_unknown_transaction_is_404(client) -> None:
    _as(_stub_key())
    response = client.post(
        "/v1/validate",
        files=[("files", ("a.png", _png(), "image/png"))],
        data={"transaction_type": "NOT_A_THING", "document_types": ["rne_extract"]},
    )
    assert response.status_code == 404


def test_a_document_type_outside_the_transaction_is_400(client) -> None:
    _as(_stub_key())
    response = _validate(client, doc_types=("auditor_report",))
    assert response.status_code == 400


def test_mismatched_files_and_types_is_400(client) -> None:
    _as(_stub_key())
    with patch.object(OCRService, "extract", _fake_extract):
        response = client.post(
            "/v1/validate",
            files=[("files", ("a.png", _png(), "image/png"))],
            data={"transaction_type": TXN, "document_types": ["rne_extract", "company_statutes"]},
        )
    assert response.status_code == 400


def test_a_malformed_declaration_is_rejected_not_ignored(client) -> None:
    _as(_stub_key())
    response = _validate(client, declaration="{not json")
    assert response.status_code == 400


# --------------------------------------------------------------------- quota

def test_each_call_is_counted(client) -> None:
    key = _stub_key()
    _as(key)

    first = _validate(client).json()
    assert first["quota"]["used"] == 1
    assert first["quota"]["remaining"] == key.monthly_quota - 1

    second = _validate(client).json()
    assert second["quota"]["used"] == 2


def test_the_period_rolls_over_on_a_new_month() -> None:
    """Rolled on read: a quota that needs a cron stops working when the cron does."""
    key = _stub_key(
        calls_this_period=900,
        period_started_at=datetime.now(UTC) - timedelta(days=40),
    )
    roll_period_if_due(key)
    assert key.calls_this_period == 0


def test_the_period_does_not_roll_within_the_same_month() -> None:
    now = datetime.now(UTC).replace(day=15)
    key = _stub_key(calls_this_period=42, period_started_at=now.replace(day=2))
    roll_period_if_due(key, now=now)
    assert key.calls_this_period == 42


# ------------------------------------------------------------------- tenancy

def test_a_validation_belongs_to_the_key_that_made_it(client) -> None:
    """Without this the twelve-hex id would be an access grant to another
    customer's dossier."""
    mine = _stub_key(owner="buyer-one@example.tn")
    _as(mine)
    validation_id = _validate(client).json()["validation_id"]
    assert client.get(f"/v1/validations/{validation_id}").status_code == 200

    _as(_stub_key(owner="buyer-two@example.tn"))
    assert client.get(f"/v1/validations/{validation_id}").status_code == 403


def test_a_dossier_filed_in_the_web_app_is_not_readable_over_the_api(
    client, store
) -> None:
    """Two products, one store. An API key buys access to its own calls."""
    submission = store.create(
        transaction_type=TXN,
        documents={},
        completeness={"status": "COMPLETE"},
        flags=[],
        status="SUBMITTED",
        owner_id="some-web-user",
    )
    _as(_stub_key())
    assert client.get(f"/v1/validations/{submission.id}").status_code == 403


def test_an_unknown_validation_is_404(client) -> None:
    _as(_stub_key())
    assert client.get("/v1/validations/doesnotexist").status_code == 404


# --------------------------------------------------------------------- usage

def test_usage_reports_consumption_without_the_secret(client) -> None:
    _as(_stub_key(calls_this_period=7))
    body = client.get("/v1/usage").json()

    assert body["calls_this_period"] == 7
    assert body["monthly_quota"] == 1000
    assert "key_hash" not in body


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(current_api_caller, None)
