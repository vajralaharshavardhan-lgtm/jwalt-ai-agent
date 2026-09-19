"""The genuinely agentic orchestrator: an Anthropic tool-use loop.

Claude decides which tool to call, in what order, when to retry a failed
step, when to replan, and when to stop -- the Python code here only
executes whatever Claude decides and feeds the result back. See
config/prompts/orchestrator_system.md for the constraints Claude operates
under (never invent data, dedupe before storing, human approval before any
send path could exist, respect the Apollo budget).
"""
from __future__ import annotations

import json
from pathlib import Path

import anthropic

from src.orchestrator import actions as A
from src.orchestrator.context import OrchestratorContext
from src.orchestrator.tools import TOOL_SCHEMAS, dispatch_tool

_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "config" / "prompts" / "orchestrator_system.md"
)


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


class MaxIterationsExceeded(Exception):
    pass


class AgenticOrchestrator:
    def __init__(
        self,
        *,
        anthropic_api_key: str,
        model: str,
        ctx: OrchestratorContext,
        max_iterations: int = 20,
        max_retries_per_step: int = 2,
    ):
        self._client = anthropic.Anthropic(api_key=anthropic_api_key)
        self._model = model
        self._ctx = ctx
        self._max_iterations = max_iterations
        self._max_retries_per_step = max_retries_per_step
        self._system_prompt = _load_system_prompt()

    def run(self, objective: str) -> str:
        messages: list[dict] = [{"role": "user", "content": objective}]
        consecutive_errors_by_tool: dict[str, int] = {}

        for iteration in range(1, self._max_iterations + 1):
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=self._system_prompt,
                tools=TOOL_SCHEMAS,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            if not tool_use_blocks:
                # Claude answered in plain text without calling `finish` -- treat as done.
                final_text = "".join(b.text for b in response.content if b.type == "text")
                self._ctx.store.run_logs.log(
                    run_id=self._ctx.run_id, agent="orchestrator", action=A.ORCHESTRATOR_FINISHED,
                    status="SUCCESS", output_summary=final_text[:500],
                )
                return final_text

            tool_results = []
            finished_summary: str | None = None

            for block in tool_use_blocks:
                self._ctx.store.run_logs.log(
                    run_id=self._ctx.run_id, agent="orchestrator", action=A.ORCHESTRATOR_STEP,
                    status="SUCCESS", input_summary=f"iteration={iteration} tool={block.name}",
                    output_summary=json.dumps(block.input)[:500],
                )
                is_error = False
                try:
                    result = dispatch_tool(block.name, block.input, self._ctx)
                    consecutive_errors_by_tool[block.name] = 0
                except Exception as exc:  # noqa: BLE001 -- any tool failure must reach Claude, not crash the run
                    count = consecutive_errors_by_tool.get(block.name, 0) + 1
                    consecutive_errors_by_tool[block.name] = count
                    result = {"error": str(exc)}
                    if count > self._max_retries_per_step:
                        result["escalation"] = (
                            f"This tool has now failed {count} times in a row. Do not retry it "
                            "again with the same arguments -- change your approach or call finish."
                        )
                    is_error = True
                    self._ctx.store.run_logs.log(
                        run_id=self._ctx.run_id, agent="orchestrator", action=block.name,
                        status="ERROR", input_summary=json.dumps(block.input)[:500],
                        error_message=str(exc),
                    )

                if block.name == "finish" and not is_error:
                    finished_summary = result.get("summary", "")

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                        "is_error": is_error,
                    }
                )

            messages.append({"role": "user", "content": tool_results})

            if finished_summary is not None:
                self._ctx.store.run_logs.log(
                    run_id=self._ctx.run_id, agent="orchestrator", action=A.ORCHESTRATOR_FINISHED,
                    status="SUCCESS", output_summary=finished_summary[:500],
                )
                return finished_summary

        raise MaxIterationsExceeded(
            f"Orchestrator did not call finish within {self._max_iterations} iterations."
        )
