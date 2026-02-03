import pytest
import pytest_asyncio
from aiohttp import web
from aiohttp.test_utils import TestServer
from app.models.feed import parse_feed, SSRFException, is_safe_redirect


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

    async def redirect_to_different_host(request):
        return web.Response(
            status=302, headers={"Location": "http://evil.com/feed.xml"}
        )

    app = web.Application()
    app.router.add_get("/redirect-localhost", redirect_to_localhost)
    app.router.add_get("/redirect-private", redirect_to_private)
    app.router.add_get("/redirect-metadata", redirect_to_metadata)
    app.router.add_get("/redirect-different-host", redirect_to_different_host)

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


class TestIsSafeRedirect:
    """Test the is_safe_redirect function."""

    def test_http_to_https_same_host(self):
        """HTTP to HTTPS upgrade on same host should be safe."""
        assert is_safe_redirect("http://example.com/feed", "https://example.com/feed")

    def test_http_to_https_same_host_with_path_change(self):
        """HTTP to HTTPS with path change on same host should be safe."""
        assert is_safe_redirect("http://example.com/old", "https://example.com/new")

    def test_same_scheme_same_host(self):
        """Same scheme redirect on same host should be safe."""
        assert is_safe_redirect("https://example.com/old", "https://example.com/new")

    def test_different_host_not_safe(self):
        """Redirect to completely different host should not be safe."""
        assert not is_safe_redirect(
            "http://example.com/feed", "http://different.org/feed"
        )

    def test_https_to_http_same_host(self):
        """HTTPS to HTTP on same host should still be safe (scheme doesn't matter)."""
        assert is_safe_redirect("https://example.com/feed", "http://example.com/feed")

    def test_case_insensitive_hostname(self):
        """Hostname comparison should be case-insensitive."""
        assert is_safe_redirect("http://Example.COM/feed", "https://example.com/feed")

    def test_subdomain_to_parent_safe(self):
        """Redirect from subdomain to parent domain should be safe."""
        assert is_safe_redirect(
            "http://blog.example.com/feed", "https://example.com/feed"
        )

    def test_parent_to_subdomain_safe(self):
        """Redirect from parent to subdomain should be safe (same parent domain)."""
        assert is_safe_redirect(
            "http://example.com/feed", "https://blog.example.com/feed"
        )

    def test_relative_url_safe(self):
        """Relative URLs are same-host by definition."""
        assert is_safe_redirect("https://example.com/old/feed", "/new/feed")

    def test_relative_url_path_only(self):
        """Relative path redirects should be safe."""
        assert is_safe_redirect("https://example.com/rss/full.xml", "/rss/index.xml")

    def test_www_prefix_added(self):
        """Adding www. prefix should be safe."""
        assert is_safe_redirect(
            "http://example.com/feed", "https://www.example.com/feed"
        )

    def test_www_prefix_removed(self):
        """Removing www. prefix should be safe."""
        assert is_safe_redirect(
            "https://www.example.com/feed", "https://example.com/feed"
        )

    def test_www_to_www_same_host(self):
        """www to www on same host should be safe."""
        assert is_safe_redirect(
            "http://www.example.com/feed", "https://www.example.com/feed"
        )

    def test_different_subdomain_same_parent_safe(self):
        """Redirect between subdomains of same parent should be safe."""
        assert is_safe_redirect(
            "http://blog.example.com/feed", "https://www.example.com/feed"
        )

    def test_feedburner_redirect_safe(self):
        """Redirects from FeedBurner should be safe."""
        assert is_safe_redirect(
            "http://feeds.feedburner.com/MyBlog", "http://example.com/feed"
        )

    def test_feedpress_redirect_safe(self):
        """Redirects from FeedPress should be safe."""
        assert is_safe_redirect(
            "http://feedpress.me/myblog", "https://example.com/feed"
        )

    def test_feedburner2_redirect_safe(self):
        """Redirects from feeds2.feedburner.com should be safe."""
        assert is_safe_redirect(
            "http://feeds2.feedburner.com/MyBlog", "https://example.com/feed"
        )

    def test_feedproxy_google_redirect_safe(self):
        """Redirects from Google FeedProxy should be safe."""
        assert is_safe_redirect(
            "http://feedproxy.google.com/myblog", "https://example.com/rss"
        )

    def test_cross_domain_not_from_proxy_unsafe(self):
        """Cross-domain redirects not from feed proxies should be unsafe."""
        assert not is_safe_redirect(
            "http://oldsite.com/feed", "https://newsite.com/feed"
        )

    def test_rss_subdomain_to_main_safe(self):
        """Redirect from rss subdomain to main domain should be safe."""
        assert is_safe_redirect(
            "http://rss.example.com/feed", "https://example.com/rss"
        )

    def test_feeds_subdomain_to_main_safe(self):
        """Redirect from feeds.wired.com to www.wired.com should be safe."""
        assert is_safe_redirect(
            "http://feeds.wired.com/wired/index", "https://www.wired.com/feed"
        )

    def test_tutsplus_subdomain_change_safe(self):
        """Redirect between tutsplus.com subdomains should be safe."""
        assert is_safe_redirect(
            "https://psd.tutsplus.com/feed", "https://design.tutsplus.com/posts.atom"
        )

    def test_company_rebrand_different_domain_unsafe(self):
        """Company rebrands to completely different domain should be unsafe."""
        assert not is_safe_redirect(
            "https://wpmu.org/feed", "https://wpmudev.com/blog/feed"
        )

    def test_company_rebrand_different_tld_unsafe(self):
        """Company rebrands with different TLD should be unsafe."""
        assert not is_safe_redirect(
            "https://gravityview.co/feed", "https://gravitykit.com/feed"
        )
