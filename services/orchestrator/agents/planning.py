"""Planning Agent — Task decomposition and dependency graph generation."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import structlog

from llm_client import LLMClient

logger = structlog.get_logger()

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class TaskType(str, Enum):
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    TEST_GENERATION = "test_generation"
    PIPELINE_DESIGN = "pipeline_design"
    MIGRATION = "migration"
    REQUIREMENTS = "requirements"


@dataclass
class Task:
    id: str
    type: TaskType
    description: str
    dependencies: list[str]
    context: dict[str, str]
    priority: int = 0


@dataclass
class ExecutionPlan:
    tasks: list[Task]
    execution_order: list[str]  # Topologically sorted task IDs


def _load_system_prompt() -> str:
    """Load the planning agent system prompt."""
    prompt_path = PROMPTS_DIR / "planning.md"
    return prompt_path.read_text(encoding="utf-8")


def _build_user_message(user_request: str, project_context: dict[str, str]) -> str:
    """Construct the user message with the request and project context."""
    parts: list[str] = []

    parts.append(f"## User Request\n{user_request}")

    if project_context:
        ctx = "\n".join(f"- {k}: {v}" for k, v in project_context.items())
        parts.append(f"\n## Project Context\n{ctx}")

    parts.append(
        "\n## Instructions\n"
        "Decompose the above request into executable tasks. "
        "Return a JSON array of task objects as specified in your system prompt."
    )

    return "\n".join(parts)


def _topological_sort(tasks: list[Task]) -> list[str]:
    """Perform a topological sort on task IDs using Kahn's algorithm."""
    task_ids = {t.id for t in tasks}
    adjacency: dict[str, list[str]] = {t.id: [] for t in tasks}
    in_degree: dict[str, int] = {t.id: 0 for t in tasks}

    for task in tasks:
        for dep in task.dependencies:
            if dep in task_ids:
                adjacency[dep].append(task.id)
                in_degree[task.id] += 1

    queue: deque[str] = deque()
    for tid, degree in in_degree.items():
        if degree == 0:
            queue.append(tid)

    order: list[str] = []
    while queue:
        current = queue.popleft()
        order.append(current)
        for neighbour in adjacency[current]:
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                queue.append(neighbour)

    # If there are remaining tasks not in order, append them (handles cycles gracefully)
    remaining = [t.id for t in tasks if t.id not in set(order)]
    if remaining:
        logger.warning("planning.topological_sort.cycle_detected", remaining_tasks=remaining)
        order.extend(remaining)

    return order


def _parse_plan_response(response: str) -> list[Task]:
    """Parse the LLM JSON response into Task objects with fallback on error."""
    try:
        # Handle markdown code blocks
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()

        data = json.loads(json_str)

        # Accept both a raw array and an object with a "tasks" key
        task_list: list[dict[str, object]] = data if isinstance(data, list) else data.get("tasks", [])

        tasks: list[Task] = []
        for item in task_list:
            raw_type = str(item.get("type", "code_generation"))
            try:
                task_type = TaskType(raw_type)
            except ValueError:
                task_type = TaskType.CODE_GENERATION

            raw_deps = item.get("dependencies", [])
            deps: list[str] = [str(d) for d in raw_deps] if isinstance(raw_deps, list) else []

            raw_ctx = item.get("context", {})
            ctx: dict[str, str] = {str(k): str(v) for k, v in raw_ctx.items()} if isinstance(raw_ctx, dict) else {}

            tasks.append(
                Task(
                    id=str(item.get("id", f"task_{len(tasks) + 1}")),
                    type=task_type,
                    description=str(item.get("description", "")),
                    dependencies=deps,
                    context=ctx,
                    priority=int(item.get("priority", 0)),
                )
            )

        return tasks

    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        logger.warning("planning.parse_failed", error=str(e))
        return []


async def create_plan(llm: LLMClient, user_request: str, project_context: dict[str, str]) -> ExecutionPlan:
    """
    Decompose a user request into an ordered set of agent tasks.

    Uses the LLM to analyze the request, identify required operations,
    and build a dependency graph for execution.
    """
    logger.info("planning.create_plan", request_length=len(user_request))

    system_prompt = _load_system_prompt()
    user_message = _build_user_message(user_request, project_context)

    response = await llm.generate(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=None,
        temperature=0.3,
    )

    tasks = _parse_plan_response(response)

    if not tasks:
        logger.warning("planning.empty_plan", request=user_request[:200])
        return ExecutionPlan(tasks=[], execution_order=[])

    execution_order = _topological_sort(tasks)

    logger.info(
        "planning.complete",
        task_count=len(tasks),
        execution_order=execution_order,
    )

    return ExecutionPlan(tasks=tasks, execution_order=execution_order)
