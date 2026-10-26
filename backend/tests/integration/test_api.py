from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.core.config import Settings
from app.main import create_app

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def make_settings(tmp_path: Path, mode: str = "fixture") -> Settings:
    return Settings(
        mode=mode,
        database_url=f"sqlite:///{(tmp_path / 'mutation_domino.db').as_posix()}",
        cache_dir=tmp_path / "cache",
        offline_fixture_dir=FIXTURES,
    )


@pytest.fixture()
def client(tmp_path):
    app = create_app(make_settings(tmp_path))
    with TestClient(app) as test_client:
        yield test_client


def create_analysis(client: TestClient, variant: str = "N10V") -> dict:
    response = client.post(
        "/api/v1/analyses",
        json={"accession": "P69905", "variant": variant},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_health(client: TestClient) -> None:
    root = client.get("/health")
    assert root.status_code == 200
    assert root.json()["status"] == "ok"
    api = client.get("/api/v1/health")
    assert api.status_code == 200
    assert api.json()["mode"] == "fixture"


def test_openapi_schema(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "/api/v1/analyses" in schema["paths"]
    assert "/api/v1/proteins/{accession}" in schema["paths"]


def test_protein_overview(client: TestClient) -> None:
    response = client.get("/api/v1/proteins/P69905")
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Hemoglobin subunit alpha"
    assert payload["length"] == 142
    assert payload["sequence"].startswith("MVLSPADK")
    assert payload["structure"]["available"] is True
    assert payload["structure"]["model_version"] == "v6"
    assert payload["structure"]["is_predicted"] is True
    assert payload["structure"]["checksum_sha256"]


def test_structure_download(client: TestClient) -> None:
    response = client.get("/api/v1/proteins/P69905/structure")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("chemical/x-mmcif")
    assert "inline" in response.headers["content-disposition"]
    assert b"_atom_site." in response.content


def test_analysis_create_get_and_export(client: TestClient) -> None:
    created = create_analysis(client)
    analysis_id = created["id"]
    result = created["result"]
    assert created["status"] == "completed"
    assert result["variant"]["normalized"] == "N10V"
    assert result["mapping"]["structure_residue_id"] == "10"
    assert result["confidence"]["availability"] == "available"
    assert result["neighborhood"]["ca_neighbors"]["count"] > 0
    assert result["neighborhood"]["heavy_atom_contacts"]["count"] > 0
    assert "mutant_structure" not in result
    assert "domino_score" not in result

    fetched = client.get(f"/api/v1/analyses/{analysis_id}")
    assert fetched.status_code == 200
    assert fetched.json()["result"] == result

    listing = client.get("/api/v1/analyses?limit=10&offset=0").json()
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == analysis_id
    assert listing["items"][0]["variant"] == "N10V"
    assert listing["items"][0]["structure_source"].startswith("AlphaFold")

    export = client.get(f"/api/v1/analyses/{analysis_id}/export.json")
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("application/json")
    assert "attachment" in export.headers["content-disposition"]
    exported = json.loads(export.content)
    assert exported["export_schema_version"] == "1.0.0"
    assert exported["analysis"]["id"] == analysis_id
    assert "clinical" in exported["disclaimer"]
    assert exported["methodology"]["parameters"]["ca_radius_angstrom"] == 8.0


def test_pdf_report_opens_and_contains_limitations(client: TestClient) -> None:
    created = create_analysis(client, variant="N10V")
    response = client.get(f"/api/v1/analyses/{created['id']}/report.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    reader = PdfReader(BytesIO(response.content))
    assert len(reader.pages) >= 1
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Mutation Domino" in text
    assert "N10V" in text
    assert "not a pathogenicity" in text
    assert "SHA-256" in text


def test_custom_parameters_are_recorded(client: TestClient) -> None:
    response = client.post(
        "/api/v1/analyses",
        json={
            "accession": "P69905",
            "variant": "N10V",
            "parameters": {"ca_radius_angstrom": 10.0, "heavy_atom_radius_angstrom": 4.0},
        },
    )
    assert response.status_code == 201
    result = response.json()["result"]
    assert result["input"]["parameters"] == {
        "ca_radius_angstrom": 10.0,
        "heavy_atom_radius_angstrom": 4.0,
    }
    assert result["neighborhood"]["ca_neighbors"]["radius_angstrom"] == 10.0


def test_analysis_persists_across_restart(tmp_path) -> None:
    settings = make_settings(tmp_path)
    with TestClient(create_app(settings)) as first:
        created = create_analysis(first)
        analysis_id = created["id"]
    with TestClient(create_app(settings)) as second:
        fetched = second.get(f"/api/v1/analyses/{analysis_id}")
        assert fetched.status_code == 200
        assert fetched.json()["result"]["variant"]["normalized"] == "N10V"
        assert second.get("/api/v1/analyses").json()["total"] == 1


@pytest.mark.parametrize(
    "body,status,code",
    [
        ({"accession": "P69905-2", "variant": "N10V"}, 422, "INVALID_ACCESSION"),
        ({"accession": "P69905", "variant": "10V"}, 422, "INVALID_VARIANT"),
        ({"accession": "P69905", "variant": "K10V"}, 422, "VARIANT_WT_MISMATCH"),
        ({"accession": "P69905", "variant": "N10N"}, 422, "INVALID_VARIANT"),
        ({"accession": "P69905", "variant": "N999V"}, 422, "INVALID_VARIANT"),
    ],
)
def test_analysis_validation_errors(client: TestClient, body: dict, status: int, code: str) -> None:
    response = client.post("/api/v1/analyses", json=body)
    assert response.status_code == status
    payload = response.json()
    assert payload["error"]["code"] == code
    assert "traceback" not in payload["error"]["message"].lower()


def test_parameter_validation_error(client: TestClient) -> None:
    response = client.post(
        "/api/v1/analyses",
        json={
            "accession": "P69905",
            "variant": "N10V",
            "parameters": {"ca_radius_angstrom": 999},
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_unknown_protein_in_fixture_mode(client: TestClient) -> None:
    response = client.get("/api/v1/proteins/P12345")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROTEIN_NOT_FOUND"
    assert "fixture" in response.json()["error"]["message"].lower()


def test_unknown_analysis(client: TestClient) -> None:
    response = client.get("/api/v1/analyses/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"


def test_list_pagination(client: TestClient) -> None:
    for variant in ("N10V", "N10A"):
        create_analysis(client, variant=variant)
    page = client.get("/api/v1/analyses?limit=1&offset=1").json()
    assert page["total"] == 2
    assert len(page["items"]) == 1
    assert page["limit"] == 1
    assert page["offset"] == 1


def test_health_does_not_require_upstream(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "ok"
