"""
@file        kumihimo/core/errors.py
@purpose     The exception vocabulary every layer shares: one base error for
             expected failures clients turn into messages, and the cycle error
             that carries its path.
@layer       core
@tags        errors, exceptions, cycles
@related     kumihimo/core/graph.py (raises CycleError),
             kumihimo/cli/README.md (clients render these, never traceback)
@design      PLAN.md §3.4
"""

from __future__ import annotations


class KumihimoError(Exception):
    """An expected failure with a message fit for the user.

    @purpose  The contract between core and its clients: anything raised as this
              is rendered as a message and an exit code, never a traceback.
    """


class CycleError(KumihimoError):
    """The plan graph contains a dependency cycle.

    @purpose  Carries the cycle as an id path so every surface (check output,
              editor diagnostics, MCP) can name it instead of shrugging.
    """

    def __init__(self, nodes: list[str]) -> None:
        """Store the cycle path and build the message from it.

        @purpose  One canonical rendering of a cycle: a -> b -> a.
        """
        self.nodes = nodes
        super().__init__("dependency cycle: " + " -> ".join([*nodes, nodes[0]]))
