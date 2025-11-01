import pytest
import pytest_asyncio
from aiohttp import web
from aiohttp.test_utils import TestServer
from app.models.feed import parse_feed, SSRFException


@pytest_asyncio.fixture
async def redirect_server():
    async def redirect_to_localhost(request):
        return web.Response(status=302, headers={"Location": "http://127.0.0.1:6379/"})

    async def redirect_to_private(request):
        return web.Response(status=302, headers={"Location": "http://192.168.1.1/"})

    async def redirect_to_metadata(request):
        return web.Response(
            status=302, headers={"Location": "http://169.254.169.254/latest/meta-data/"}
        )

    app = web.Application()
    app.router.add_get("/redirect-localhost", redirect_to_localhost)
    app.router.add_get("/redirect-private", redirect_to_private)
    app.router.add_get("/redirect-metadata", redirect_to_metadata)

    server = TestServer(app)
    await server.start_server()
    yield server
    await server.close()


@pytest.mark.asyncio
async def test_ssrf_direct_localhost():
    with pytest.raises(SSRFException):
        await parse_feed("http://127.0.0.1/feed.xml")


@pytest.mark.asyncio
async def test_ssrf_direct_private_ip():
    with pytest.raises(SSRFException):
        await parse_feed("http://192.168.1.1/feed.xml")


@pytest.mark.asyncio
async def test_ssrf_direct_link_local():
    with pytest.raises(SSRFException):
        await parse_feed("http://169.254.169.254/feed.xml")


@pytest.mark.asyncio
async def test_ssrf_redirect_to_localhost(redirect_server):
    url = f"http://{redirect_server.host}:{redirect_server.port}/redirect-localhost"
    with pytest.raises(SSRFException):
        await parse_feed(url)


@pytest.mark.asyncio
async def test_ssrf_redirect_to_private_ip(redirect_server):
    url = f"http://{redirect_server.host}:{redirect_server.port}/redirect-private"
    with pytest.raises(SSRFException):
        await parse_feed(url)


@pytest.mark.asyncio
async def test_ssrf_redirect_to_metadata_service(redirect_server):
    url = f"http://{redirect_server.host}:{redirect_server.port}/redirect-metadata"
    with pytest.raises(SSRFException):
        await parse_feed(url)
