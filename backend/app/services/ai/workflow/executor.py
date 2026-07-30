import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.services.ai.workflow.nodes import NODE_REGISTRY

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    def __init__(self, instance: Any, services: dict[str, Any]) -> None:
        self.instance = instance
        self.services = services
        wf_def = instance.workflow.definition
        self.definition = json.loads(wf_def) if isinstance(wf_def, str) else wf_def
        ctx = instance.context
        self.context: dict = json.loads(ctx) if isinstance(ctx, str) else (ctx or {})

    def _find_node(self, node_id: str) -> dict | None:
        for n in self.definition.get("nodes", []):
            if n["id"] == node_id:
                return n
        return None

    def _find_start_node(self) -> dict:
        for n in self.definition.get("nodes", []):
            if n["type"] == "start":
                return n
        raise ValueError("No start node found")

    def _validate_dag(self) -> None:
        nodes = {n["id"] for n in self.definition.get("nodes", [])}
        edges = self.definition.get("edges", [])
        in_degree = {n: 0 for n in nodes}
        adj = {n: [] for n in nodes}
        for e in edges:
            if e["source"] in adj and e["target"] in nodes:
                adj[e["source"]].append(e["target"])
                in_degree[e["target"]] = in_degree.get(e["target"], 0) + 1
        queue = [n for n, d in in_degree.items() if d == 0]
        visited = 0
        while queue:
            node = queue.pop(0)
            visited += 1
            for nb in adj.get(node, []):
                in_degree[nb] -= 1
                if in_degree[nb] == 0:
                    queue.append(nb)
        if visited != len(nodes):
            raise ValueError("DAG contains a cycle")

    def _find_next(self, node: dict, result: dict) -> str | None:
        edges = self.definition.get("edges", [])
        outgoing = [e for e in edges if e["source"] == node["id"]]
        if not outgoing:
            return None
        if node["type"] == "condition":
            branch = "true" if result.get("result") else "false"
            match = [e for e in outgoing if e.get("label") == branch]
            return match[0]["target"] if match else None
        return outgoing[0]["target"]

    async def execute(self, input_data: dict | None = None) -> None:
        self._validate_dag()
        self.instance.status = "running"
        self.instance.started_at = datetime.now(timezone.utc)
        self.context["input"] = input_data or {}
        if "outputs" not in self.context:
            self.context["outputs"] = {}

        current_id = self._find_start_node()["id"]
        while current_id:
            node = self._find_node(current_id)
            if not node:
                break
            impl = NODE_REGISTRY.get(node["type"])
            if not impl:
                self.instance.status = "failed"
                return
            try:
                result = await impl.execute(node.get("config", {}), self.context, self.services)
                self.context["outputs"][current_id] = result
            except Exception as e:
                logger.exception("Node %s failed", current_id)
                self.context["outputs"][current_id] = {"error": str(e)}
                self.instance.status = "failed"
                self.instance.context = json.dumps(self.context)
                return

            if node["type"] == "human":
                self.instance.status = "waiting_human"
                self.instance.current_node_id = node["id"]
                self.instance.context = json.dumps(self.context)
                return

            next_id = self._find_next(node, result)
            if not next_id:
                break
            current_id = next_id

        self.instance.status = "completed"
        self.instance.completed_at = datetime.now(timezone.utc)
        self.instance.context = json.dumps(self.context)

    async def resume_after_review(self, approved: bool, comment: str | None = None) -> None:
        if self.instance.status != "waiting_human":
            raise ValueError("Not in waiting_human status")
        current_id = self.instance.current_node_id
        node = self._find_node(current_id) if current_id else None
        if not node:
            self.instance.status = "failed"
            return
        self.context["outputs"][current_id] = {"approved": approved, "comment": comment, "status": "approved" if approved else "rejected"}
        if not approved:
            self.instance.status = "completed"
            self.instance.completed_at = datetime.now(timezone.utc)
            self.instance.context = json.dumps(self.context)
            return
        self.instance.status = "running"
        self.instance.current_node_id = None
        next_id = self._find_next(node, {"result": True})
        while next_id:
            n = self._find_node(next_id)
            if not n:
                break
            impl = NODE_REGISTRY.get(n["type"])
            if not impl:
                self.instance.status = "failed"
                return
            try:
                res = await impl.execute(n.get("config", {}), self.context, self.services)
                self.context["outputs"][next_id] = res
            except Exception as e:
                self.context["outputs"][next_id] = {"error": str(e)}
                self.instance.status = "failed"
                self.instance.context = json.dumps(self.context)
                return
            if n["type"] == "human":
                self.instance.status = "waiting_human"
                self.instance.current_node_id = n["id"]
                self.instance.context = json.dumps(self.context)
                return
            next_id = self._find_next(n, res)
        self.instance.status = "completed"
        self.instance.completed_at = datetime.now(timezone.utc)
        self.instance.context = json.dumps(self.context)
