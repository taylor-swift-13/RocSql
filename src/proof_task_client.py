#!/usr/bin/env python3
"""
Extensible LLM proof-task client.

Design goals:
- One client binds a fixed theorem_id (repo/compile_args are fixed accordingly)
- Tool registry architecture for future extensibility
- Model returns JSON actions only; client executes tools and feeds results back
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple

from coq_print import execute_print_command
from verify import CoqProofVerifier

# =========================
# OpenAI configuration
# =========================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = "https://yunwu.ai/v1"



@dataclass
class TaskContext:
    theorem_id: str
    project: str
    file_relpath: str
    repo_path: str
    compile_args: List[str]
    theorem_statement: str
    header_context: str
    upper_context: str


class Tool(Protocol):
    name: str

    def spec(self) -> Dict[str, Any]:
        ...

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        ...


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def specs(self) -> List[Dict[str, Any]]:
        return [t.spec() for t in self._tools.values()]

    def validate_and_dispatch(self, action_obj: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], str]:
        action = action_obj.get("action")
        if not isinstance(action, str):
            return None, "action 必须是字符串"
        tool = self.get(action)
        if tool is None:
            return None, f"未知 action: {action}"
        args = action_obj.get("args", {})
        if not isinstance(args, dict):
            return None, "args 必须是 JSON object"
        return tool.run(args), ""


class VerifyProofTool:
    name = "verify_proof"

    def __init__(self, verifier: CoqProofVerifier, theorem_id: str):
        self.verifier = verifier
        self.theorem_id = theorem_id

    def spec(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "验证证明内容。固定 theorem_id，不需要传 theorem_id。",
            "args_schema": {
                "type": "object",
                "required": ["proof"],
                "properties": {
                    "proof": {"type": "string", "description": "证明文本，可完整或未完成"},
                },
            },
        }

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        proof = args.get("proof", "")
        if not isinstance(proof, str) or not proof.strip():
            return {"success": False, "error": "proof 不能为空字符串"}
        return self.verifier.verify_proof(self.theorem_id, proof)


class PrintDefinitionTool:
    name = "print"

    def __init__(self, repo_path: str, compile_args: List[str]):
        self.repo_path = repo_path
        self.compile_args = compile_args

    def spec(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "打印定义。固定 repo/compile_args，仅需传定义名。",
            "args_schema": {
                "type": "object",
                "required": ["definition"],
                "properties": {
                    "definition": {"type": "string", "description": "定义名，例如 unique_key_in"},
                },
            },
        }

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        definition = args.get("definition", "")
        if not isinstance(definition, str) or not definition.strip():
            return {"success": False, "error": "definition 不能为空字符串"}
        cmd = f"Print {definition.strip()}."
        return execute_print_command(
            query_command=cmd,
            compile_args=self.compile_args,
            cwd=self.repo_path,
        )


class ModelDriver(Protocol):
    def next(self, messages: List[Dict[str, str]]) -> str:
        ...


class OpenAIModelDriver:
    def __init__(self, model: str):
        self.model = model

    def next(self, messages: List[Dict[str, str]]) -> str:
        from openai import OpenAI  # type: ignore

        client = OpenAI()
        resp = client.chat.completions.create(
            model=self.model,
            temperature=0.0,
            messages=messages,  # type: ignore[arg-type]
        )
        return (resp.choices[0].message.content or "").strip()


class OpenAIModelDriver:
    """Use OpenAI SDK with key from environment variable OPENAI_API_KEY."""

    def __init__(self, model: str = "gpt-5-nano"):
        self.model = model
        self.api_key = OPENAI_API_KEY
        self.base_url = OPENAI_BASE_URL
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is empty. Set it in your shell environment before running.")

    @staticmethod
    def _build_query(messages: List[Dict[str, str]]) -> str:
        parts: List[str] = []
        parts.append("You must return exactly one JSON object. No markdown. No explanations.")
        parts.append("Conversation history follows. Continue based on the latest user message.")
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            parts.append(f"[{role}]\n{content}")
        parts.append(
            "再次强调：仅输出 JSON。格式如 "
            '{"action":"verify_proof","args":{"proof":"Proof. ..."}} '
            '或 {"action":"print","args":{"definition":"foo"}} '
            '或 {"action":"final","proof":"Proof. ... Qed.","reason":"..."}'
        )
        return "\n\n".join(parts)

    def next(self, messages: List[Dict[str, str]]) -> str:
        from openai import OpenAI  # type: ignore

        query = self._build_query(messages)
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        resp = client.chat.completions.create(
            model=self.model,
            temperature=0.0,
            messages=[{"role": "user", "content": query}],
        )
        return (resp.choices[0].message.content or "").strip()


class ProofTaskClient:
    def __init__(self, theorem_id: str, context_lines: int = 80, coqstoq_path: Optional[str] = None):
        self.verifier = CoqProofVerifier(coqstoq_path=coqstoq_path)
        self.task = self._build_task_context(theorem_id, context_lines)
        self.registry = ToolRegistry()
        self._register_builtin_tools()

    def _build_task_context(self, theorem_id: str, m: int) -> TaskContext:
        split_name, index = self.verifier._parse_theorem_id(theorem_id)  # pylint: disable=protected-access
        theorem_def = self.verifier._load_theorem_definition(split_name, index)  # pylint: disable=protected-access
        if theorem_def is None:
            raise ValueError(f"Theorem not found: {theorem_id}")

        repo_path = os.path.join(
            self.verifier.coqstoq_path,
            theorem_def["project"]["split"]["dir_name"],
            theorem_def["project"]["dir_name"],
        )
        src_file = os.path.join(repo_path, theorem_def["path"])
        if not os.path.exists(src_file):
            raise FileNotFoundError(f"Source file not found: {src_file}")

        with open(src_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        theorem_start_line = theorem_def["theorem_start_pos"]["line"]
        theorem_statement = self.verifier._extract_theorem_statement(repo_path, theorem_def)  # pylint: disable=protected-access
        compile_args = theorem_def["project"].get("compile_args", [])

        prefixes = (
            "From ",
            "Require ",
            "Import ",
            "Export ",
            "Open Scope ",
            "Local Open Scope ",
            "Set ",
            "Unset ",
        )
        headers = [ln.rstrip("\n") for ln in lines[:theorem_start_line] if ln.lstrip().startswith(prefixes)]
        header_context = "\n".join(headers[-120:]) if headers else "(无显式头部依赖语句)"

        start = max(0, theorem_start_line - m)
        upper_context = "".join(lines[start:theorem_start_line]).rstrip("\n")
        if not upper_context.strip():
            upper_context = "(No additional local context before theorem)"

        return TaskContext(
            theorem_id=theorem_id,
            project=theorem_def["project"]["dir_name"],
            file_relpath=theorem_def["path"],
            repo_path=repo_path,
            compile_args=compile_args,
            theorem_statement=theorem_statement,
            header_context=header_context,
            upper_context=upper_context,
        )

    def _register_builtin_tools(self) -> None:
        self.registry.register(VerifyProofTool(self.verifier, self.task.theorem_id))
        self.registry.register(PrintDefinitionTool(self.task.repo_path, self.task.compile_args))

    def register_tool(self, tool: Tool) -> None:
        """可扩展入口：允许后续继续新增工具。"""
        self.registry.register(tool)

    def build_system_prompt(self) -> str:
        tool_specs = json.dumps(self.registry.specs(), ensure_ascii=False, indent=2)
        return f"""You are a Coq proof assistant. You must call tools via JSON actions.

Task info:
- theorem_id: {self.task.theorem_id}
- project: {self.task.project}
- file: {self.task.file_relpath}
- repo_path: {self.task.repo_path}
- compile_args: {self.task.compile_args}

Available tools:
{tool_specs}

You must return exactly one of the following JSON objects:
1) Tool call
{{"action":"verify_proof","args":{{"proof":"Proof. ..."}}}}
{{"action":"print","args":{{"definition":"foo"}}}}
2) Finish
{{"action":"final","proof":"Proof. ... Qed.","reason":"short explanation"}}

Do not return markdown. Do not return any extra text.

Proof strategy guidance:
- You may first attempt a full proof in one shot up to `Qed.`.
- If that fails, switch to iterative exploration:
  - step-by-step (one small step each turn), or
  - multi-steps per turn (a few tactics each turn).
- Use `verify_proof` frequently to debug and refine.
- Use `print` whenever you need to inspect definitions/lemmas.

Context:
[Theorem Statement]
{self.task.theorem_statement}

[Header Context]
{self.task.header_context}

[Upper Context: previous lines]
{self.task.upper_context}
"""

    def build_initial_user_prompt(self) -> str:
        return "Start proving iteratively. Use `print` to inspect definitions, `verify_proof` to validate attempts, and return `final` when done."


def parse_action(raw: str) -> Tuple[Optional[Dict[str, Any]], str]:
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, f"JSON parse failed: {e}"
    if not isinstance(obj, dict):
        return None, "Response must be a JSON object"
    action = obj.get("action")
    if action not in {"verify_proof", "print", "final"}:
        return None, "action must be one of: verify_proof / print / final"
    return obj, ""


def run_loop(client: ProofTaskClient, driver: ModelDriver, max_steps: int) -> Dict[str, Any]:
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": client.build_system_prompt()},
        {"role": "user", "content": client.build_initial_user_prompt()},
    ]

    for step in range(1, max_steps + 1):
        raw = driver.next(messages)
        messages.append({"role": "assistant", "content": raw})

        action_obj, err = parse_action(raw)
        if action_obj is None:
            feedback = {"success": False, "error": err, "raw_model_output": raw}
            messages.append({"role": "user", "content": "Tool execution result:\n" + json.dumps(feedback, ensure_ascii=False)})
            continue

        if action_obj["action"] == "final":
            return {"success": True, "steps_used": step, "final": action_obj, "messages": messages}

        tool_result, dispatch_err = client.registry.validate_and_dispatch(action_obj)
        if tool_result is None:
            tool_result = {"success": False, "error": dispatch_err}

        feedback = {"tool": action_obj["action"], "result": tool_result}
        messages.append({"role": "user", "content": "Tool execution result:\n" + json.dumps(feedback, ensure_ascii=False)})

    return {"success": False, "error": f"Reached max steps ({max_steps}) without final", "messages": messages}


def main() -> None:
    parser = argparse.ArgumentParser("Extensible fixed-theorem proof-task client.")
    parser.add_argument("--theorem-id", required=True, help="e.g. test:39")
    parser.add_argument("--context-lines", type=int, default=80, help="Number of lines before theorem as local context")
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model name")
    parser.add_argument("--dump-system-prompt", action="store_true", help="Print system prompt only")
    args = parser.parse_args()

    client = ProofTaskClient(theorem_id=args.theorem_id, context_lines=args.context_lines)
    if args.dump_system_prompt:
        print(client.build_system_prompt())
        return

    driver: ModelDriver = OpenAIModelDriver(model=args.model)

    result = run_loop(client=client, driver=driver, max_steps=args.max_steps)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
