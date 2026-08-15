import unittest
from unittest import mock
import urllib.error
import urllib.request

from apr.llm.openai_compat import _urlopen_with_fallback


class ProxyFallbackTest(unittest.TestCase):
    def test_retry_direct_when_proxy_refused(self):
        fake_resp = mock.MagicMock()
        fake_opener = mock.MagicMock()
        fake_opener.open.return_value = fake_resp
        req = urllib.request.Request("https://api.deepseek.com/")
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")), \
             mock.patch("urllib.request.build_opener", return_value=fake_opener):
            resp = _urlopen_with_fallback(req, 30)
        self.assertIs(resp, fake_resp)
        fake_opener.open.assert_called_once()   # 走了直连回退

    def test_no_fallback_on_http_error(self):
        # HTTP 4xx/5xx 说明网络通，不回退（避免掩盖真实错误）
        req = urllib.request.Request("https://api.deepseek.com/")
        with mock.patch("urllib.request.urlopen",
                        side_effect=urllib.error.HTTPError(req.full_url, 401, "unauthorized", {}, None)), \
             mock.patch("urllib.request.build_opener") as m:
            with self.assertRaises(urllib.error.HTTPError):
                _urlopen_with_fallback(req, 30)
        m.assert_not_called()

    def test_success_first_try(self):
        fake_resp = mock.MagicMock()
        req = urllib.request.Request("https://api.deepseek.com/")
        with mock.patch("urllib.request.urlopen", return_value=fake_resp), \
             mock.patch("urllib.request.build_opener") as m:
            resp = _urlopen_with_fallback(req, 30)
        self.assertIs(resp, fake_resp)
        m.assert_not_called()
