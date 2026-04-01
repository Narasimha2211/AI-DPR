"""
AI DPR - API Integration Tests
Tests for FastAPI endpoints.
"""

import pytest
import sys
from pathlib import Path
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health_check():
    """Test the health check endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.anyio
async def test_supported_formats():
    """Test supported file formats endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/upload/supported-formats")
        assert resp.status_code == 200
        data = resp.json()
        assert "pdf" in [f.lower() for f in data.get("formats", [])]


@pytest.mark.anyio
async def test_supported_states():
    """Test supported states endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/upload/supported-states")
        assert resp.status_code == 200
        data = resp.json()
        assert "mdoner_states" in data
        assert len(data["mdoner_states"]) == 8


@pytest.mark.anyio
async def test_grading_system():
    """Test grading system endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/dashboard/grading-system")
        assert resp.status_code == 200
        data = resp.json()
        assert "grades" in data


@pytest.mark.anyio
async def test_upload_no_file():
    """Test upload endpoint with no file returns error."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/upload/dpr")
        assert resp.status_code in [400, 422]


@pytest.mark.anyio
async def test_dashboard_stats():
    """Test dashboard stats endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_dprs_analyzed" in data


@pytest.mark.anyio
async def test_root_endpoint():
    """Test root endpoint returns HTML or redirect."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
