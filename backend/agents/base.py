from pathlib import Path

from backend.llm.client import LLMClient
from backend.rag.retriever import Retriever
from backend.schemas import ChatResponse, Source


GENERAL_CHAT_TRIGGERS = (
    "你在说什么",
    "你说什么",
    "什么意思",
    "没看懂",
    "答非所问",
    "你是谁",
    "你能做什么",
    "hello",
    "hi",
)

PROJECT_TERMS = (
    "apdu",
    "tlv",
    "pboc",
    "java card",
    "javacard",
    "applet",
    "cos",
    "usim",
    "emv",
    "gpo",
    "select",
    "代码",
    "源码",
    "方法",
    "函数",
    "类",
    "文件",
    "流程",
    "规范",
    "协议",
)


class BaseAgent:
    mode: str
    prompt_file: str

    def __init__(self, settings) -> None:
        self.settings = settings
        self.retriever = Retriever(settings)
        self.llm = LLMClient(settings)

    @property
    def system_prompt(self) -> str:
        path = Path(__file__).resolve().parents[1] / "prompts" / self.prompt_file
        return path.read_text(encoding="utf-8").strip()

    def answer(self, query: str, top_k: int | None = None) -> ChatResponse:
        if self._is_general_chat(query):
            return ChatResponse(answer=self._answer_general_chat(query), sources=[])

        chunks = self.retriever.retrieve(query=query, mode=self.mode, top_k=top_k)
        context = self._format_context(chunks)
        prompt = (
            "Answer only from the retrieved project knowledge below. "
            "If the answer is not present, say exactly what is missing. "
            "Do not add plausible implementation details that are not in the snippets.\n\n"
            f"{context}\n\n"
            f"User question:\n{query}"
        )
        answer = self.llm.complete(self.system_prompt, prompt)
        return ChatResponse(
            answer=answer,
            sources=[
                Source(
                    content=chunk["content"],
                    metadata=chunk["metadata"],
                    score=chunk.get("score"),
                )
                for chunk in chunks
            ],
        )

    def _is_general_chat(self, query: str) -> bool:
        normalized = query.strip().lower()
        if any(trigger in normalized for trigger in GENERAL_CHAT_TRIGGERS):
            return not any(term in normalized for term in PROJECT_TERMS)
        return False

    def _answer_general_chat(self, query: str) -> str:
        normalized = query.strip().lower()
        if "答非所问" in normalized:
            return (
                "你说得对。刚才我把你的普通追问也强行走了代码检索，"
                "所以拿 PBOC 源码片段来回答，方向错了。现在这类澄清问题会直接回答，"
                "只有明确问 Java Card、PBOC、APDU、源码或规范时才检索项目资料。"
            )
        if "你在说什么" in normalized or "你说什么" in normalized or "什么意思" in normalized:
            return (
                "我刚才是在解释这个本地 Java Card LLM Agent 的运行状态和性能瓶颈。"
                "如果你问项目代码、PBOC、APDU 或 Java Card 细节，我会查本地资料回答；"
                "如果只是普通追问，我会直接说明，不再硬贴源码检索结果。"
            )
        if "你是谁" in normalized or "你能做什么" in normalized:
            return (
                "我是这个本地 Java Card LLM Agent 的网页聊天入口。"
                "当前主要能基于已导入的 PBOC Java Card 源码回答问题，并附上命中的来源。"
            )
        return "我在。你可以直接问 PBOC、APDU、Java Card applet 源码相关问题。"

    def _format_context(self, chunks: list[dict]) -> str:
        if not chunks:
            return "Retrieved context: none."
        blocks = []
        for index, chunk in enumerate(chunks, start=1):
            meta = chunk["metadata"]
            source = meta.get("source", "unknown")
            heading = meta.get("heading")
            title = f"[{index}] {source}"
            if heading:
                title += f" :: {heading}"
            blocks.append(f"{title}\n{chunk['content']}")
        return "Retrieved context:\n\n" + "\n\n---\n\n".join(blocks)
