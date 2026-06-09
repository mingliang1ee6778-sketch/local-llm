import json
import os
import time
import unittest
import urllib.error
import urllib.request


BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8000")
RUN_INTEGRATION = os.getenv("LOCAL_LLM_RUN_INTEGRATION") == "1"


def _request(method: str, path: str, body: dict | None = None, timeout: int = 180):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content = response.read()
        content_type = response.headers.get("Content-Type", "")
        return response.status, content_type, content


@unittest.skipUnless(
    RUN_INTEGRATION,
    "set LOCAL_LLM_RUN_INTEGRATION=1 to hit the real web app, RAG, and Ollama",
)
class WebIntegrationTest(unittest.TestCase):
    def test_home_page_is_served(self) -> None:
        status, content_type, content = _request("GET", "/")

        html = content.decode("utf-8", errors="replace")
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn("Java Card", html)

    def test_general_chat_does_not_return_sources(self) -> None:
        status, _, content = _request(
            "POST",
            "/chat",
            {"mode": "applet", "query": "你在说什么。", "top_k": 3},
        )

        payload = json.loads(content.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["sources"], [])
        self.assertIn("answer", payload)

    def test_project_question_hits_real_rag_and_ollama(self) -> None:
        started = time.monotonic()
        status, _, content = _request(
            "POST",
            "/chat",
            {
                "mode": "applet",
                "query": "APDU 处理是怎么分发到 PSE、PPSE 和普通 PBOC 实例的？",
                "top_k": 3,
            },
            timeout=240,
        )
        elapsed = time.monotonic() - started

        payload = json.loads(content.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertGreater(len(payload["answer"].strip()), 0)
        self.assertGreater(len(payload["sources"]), 0)
        self.assertLess(elapsed, 240)


if __name__ == "__main__":
    try:
        unittest.main()
    except urllib.error.URLError as exc:
        raise SystemExit(f"Integration target unavailable: {BASE_URL}: {exc}") from exc
