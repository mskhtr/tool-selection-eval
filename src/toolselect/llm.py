from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LLMResult:
    text: str
    model_id: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
    latency_s: float | None = None
    error: str | None = None
    raw_saved: dict | None = field(default=None)


class LLMClient:
    model_id: str

    def complete(self, *, system: str, user: str, case_id: str) -> LLMResult:
        raise NotImplementedError


class ReplayLLM(LLMClient):
    """保存済みのモデル応答を返す。応答が無いケースは未実行としてエラーにする。"""

    def __init__(self, model_id: str, responses: dict[str, str]):
        self.model_id = model_id
        self.responses = responses

    def complete(self, *, system: str, user: str, case_id: str) -> LLMResult:
        if case_id not in self.responses:
            return LLMResult(text="", model_id=self.model_id, error="response_missing")
        return LLMResult(text=self.responses[case_id], model_id=self.model_id)


class FakeLLM(LLMClient):
    def __init__(self, model_id: str, handler):
        self.model_id = model_id
        self.handler = handler

    def complete(self, *, system: str, user: str, case_id: str) -> LLMResult:
        return self.handler(system=system, user=user, case_id=case_id)
