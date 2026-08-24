"""
@file        kumihimo/mcp/server.py
@purpose     Builds the MCPServer stdio server for one plan root: eleven tools,
             flat, no tiers, each a closure over tools.py. KumihimoErrors
             propagate as tool errors carrying their message.
@layer       mcp
@tags        mcp, mcpserver, stdio, registration
@related     kumihimo/mcp/tools.py (the behavior),
             kumihimo/cli/mcp_cmd.py (the verb that runs this)
@design      PLAN.md §6.1
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server import MCPServer

from kumihimo.mcp import tools

_INSTRUCTIONS = (
    "This server controls one Kumihimo plan: a graph of plain-text node files "
    "that braids into a prompt. Orient with get_plan, read prose with "
    "get_node, mutate with add_node/update_node/remove_node/link/unlink/"
    "rename_node (files are the only truth; every write lands on disk "
    "immediately), validate with check, ask ready for unblocked work, and "
    "compile with braid."
)


def build_server(root: Path) -> MCPServer:
    """The MCP server for one plan directory.

    @purpose  One server per plan keeps every tool signature free of path
              arguments an agent could get wrong.
    """
    server = MCPServer("kumihimo", instructions=_INSTRUCTIONS)

    @server.tool()
    def get_plan() -> dict[str, Any]:
        """The whole graph — manifest meta plus every node's identity, edges,
        and fields (bodies elided; use get_node)."""
        return tools.get_plan(root)

    @server.tool()
    def get_node(node_id: str) -> dict[str, Any]:
        """One node in full: edges, fields (raw and effective), and the prose body."""
        return tools.get_node(root, node_id)

    @server.tool()
    def add_node(
        node_id: str,
        kind: str,
        title: str | None = None,
        body: str = "",
        fields: dict[str, Any] | None = None,
        needs: list[str] | None = None,
        in_: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a node (id is a lowercase slug; every needs/in_ target must already exist)."""
        return tools.add_node(root, node_id, kind, title, body, fields, needs, in_)

    @server.tool()
    def update_node(
        node_id: str,
        kind: str | None = None,
        title: str | None = None,
        body: str | None = None,
        priority: int | None = None,
        set_fields: dict[str, Any] | None = None,
        unset_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Change a node's kind, title, body, priority, or kind-defined fields
        (hand-written comments in the file survive)."""
        return tools.update_node(
            root, node_id, kind, title, body, priority, set_fields, unset_fields
        )

    @server.tool()
    def remove_node(node_id: str, force: bool = False) -> dict[str, Any]:
        """Delete a node. Refuses while referenced (naming referrers) unless
        force strips the references too."""
        return tools.remove_node(root, node_id, force)

    @server.tool()
    def link(
        src: str,
        needs: str | None = None,
        in_: str | None = None,
        to: str | None = None,
        rel: str = "see-also",
    ) -> dict[str, Any]:
        """Draw exactly one edge from src: needs= (dependency; refused with the
        path if it closes a cycle), in_= (membership), or to=/rel=
        (annotation)."""
        return tools.link(root, src, needs, in_, to, rel)

    @server.tool()
    def unlink(
        src: str,
        needs: str | None = None,
        in_: str | None = None,
        to: str | None = None,
    ) -> dict[str, Any]:
        """Remove exactly one edge from src (absent edges error rather than shrug)."""
        return tools.unlink(root, src, needs, in_, to)

    @server.tool()
    def rename_node(old: str, new: str) -> dict[str, Any]:
        """Move a node to a new id: file renamed bytes-untouched, every referrer
        and the view layout fixed."""
        return tools.rename_node(root, old, new)

    @server.tool()
    def check() -> list[dict[str, str]]:
        """Every validation finding (errors first): cycles with paths, dangling
        edges, field breaches, orphans, open dependencies."""
        return tools.check(root)

    @server.tool()
    def braid(
        strategy: str | None = None,
        where: dict[str, str] | None = None,
        from_: str | None = None,
        until: str | None = None,
        in_: str | None = None,
        diagram: bool | None = None,
        dry: bool = False,
    ) -> dict[str, Any]:
        """Compile the plan (or a slice) into one deterministic prompt. Slices:
        where= field filters, from_=/until= dependency cones, in_= one
        group's members. dry=True returns just the order."""
        return tools.braid(root, strategy, where, from_, until, in_, diagram, dry)

    @server.tool()
    def ready() -> list[dict[str, Any]]:
        """Nodes ready to work on now: own status todo, every dependency
        satisfied (no status field, or status done/settled/answered)."""
        return tools.ready(root)

    return server
