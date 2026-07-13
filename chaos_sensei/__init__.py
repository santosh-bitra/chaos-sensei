"""
Chaos Sensei: Repo-aware chaos engineering and incident training agent.

A framework for creating controlled, reversible failures in safe environments
to practice incident response and debugging skills.
"""

__version__ = "0.1.0"
__author__ = "Chaos Sensei Contributors"

from chaos_sensei.core.engine import ChaosSenseiEngine

__all__ = [
    "ChaosSenseiEngine",
    "__version__",
    "__author__",
]
