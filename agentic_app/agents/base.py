from __future__ import annotations

from abc import ABC, abstractmethod

from agentic_app.models import CaseState


class BaseAgent(ABC):
    @abstractmethod
    def run(self, case_state: CaseState) -> CaseState:
        raise NotImplementedError

