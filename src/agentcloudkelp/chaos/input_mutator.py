from __future__ import annotations

import random


class InputMutator:
    def __init__(self, config=None, rng: random.Random | None = None, *, mutation_type: str | None = None, payload: str = ""):
        if config is None and mutation_type is not None:
            from types import SimpleNamespace

            config = SimpleNamespace(
                input_mutations=[SimpleNamespace(type=mutation_type, payload=payload)]
            )
        self.config = config
        self.rng = rng or random.Random()

    def mutate(self, message: str) -> str:
        mutations = getattr(self.config, "input_mutations", []) or []
        for mutation in mutations:
            kind = getattr(mutation.type, "value", mutation.type)
            if kind == "prompt_injection":
                message = f"{message}\n\n{mutation.payload}"
            elif kind == "typo":
                message = self._typo(message)
            elif kind == "unicode":
                message = self._unicode(message)
            elif kind == "multi_language":
                message = self._multi_language(message, mutation.payload)
        return message

    def _typo(self, message: str) -> str:
        if len(message) < 2:
            return message
        index = self.rng.randrange(len(message) - 1)
        chars = list(message)
        chars[index], chars[index + 1] = chars[index + 1], chars[index]
        return "".join(chars)

    def _unicode(self, message: str) -> str:
        return f"\u200b{message}\u202e"

    def _multi_language(self, message: str, payload: str) -> str:
        split = max(1, len(message) // 2)
        return f"{message[:split]} {payload} {message[split:]}"
