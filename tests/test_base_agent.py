import unittest

from backend.agents.base import BaseAgent


class FakeRetriever:
    def __init__(self) -> None:
        self.calls = []

    def retrieve(self, query: str, mode: str, top_k: int | None = None) -> list[dict]:
        self.calls.append({"query": query, "mode": mode, "top_k": top_k})
        return [
            {
                "content": "GPO is handled by the PBOC applet command dispatcher.",
                "metadata": {"source": "PBOC.java", "heading": "processGPO"},
                "score": 0.12,
            }
        ]


class FakeLLM:
    def __init__(self) -> None:
        self.calls = []

    def complete(self, system_prompt: str, prompt: str) -> str:
        self.calls.append({"system_prompt": system_prompt, "prompt": prompt})
        return "RAG answer"


class TestAgent(BaseAgent):
    mode = "applet"
    prompt_file = "applet.txt"

    def __init__(self) -> None:
        self.retriever = FakeRetriever()
        self.llm = FakeLLM()


class BaseAgentRoutingTest(unittest.TestCase):
    def test_general_followup_does_not_retrieve_project_sources(self) -> None:
        agent = TestAgent()

        response = agent.answer("你在说什么。", top_k=3)

        self.assertEqual(response.sources, [])
        self.assertEqual(agent.retriever.calls, [])
        self.assertIn("普通追问", response.answer)

    def test_general_complaint_does_not_retrieve_project_sources(self) -> None:
        agent = TestAgent()

        response = agent.answer("你刚才答非所问。")

        self.assertEqual(response.sources, [])
        self.assertEqual(agent.retriever.calls, [])
        self.assertIn("方向错了", response.answer)

    def test_project_question_uses_retriever_and_llm(self) -> None:
        agent = TestAgent()

        response = agent.answer("APDU 处理是怎么分发到 PSE、PPSE 和普通 PBOC 实例的？", top_k=5)

        self.assertEqual(response.answer, "RAG answer")
        self.assertEqual(len(response.sources), 1)
        self.assertEqual(
            agent.retriever.calls,
            [
                {
                    "query": "APDU 处理是怎么分发到 PSE、PPSE 和普通 PBOC 实例的？",
                    "mode": "applet",
                    "top_k": 5,
                }
            ],
        )
        self.assertEqual(len(agent.llm.calls), 1)
        self.assertIn("Retrieved context", agent.llm.calls[0]["prompt"])
        self.assertIn("PBOC.java", agent.llm.calls[0]["prompt"])

    def test_project_term_overrides_general_trigger(self) -> None:
        agent = TestAgent()

        response = agent.answer("你在说什么，APDU 的 GPO 是什么？")

        self.assertEqual(response.answer, "RAG answer")
        self.assertEqual(len(agent.retriever.calls), 1)


if __name__ == "__main__":
    unittest.main()
