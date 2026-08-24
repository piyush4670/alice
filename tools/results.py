"""The shared tool result type.

Lives apart from the registry so handler modules can import it without
creating an import cycle.
"""


class ToolResult:

    def __init__(self, ok: bool, output: str, data=None):
        self.ok = ok
        self.output = output
        self.data = data

    def observe(self) -> str:

        if self.ok:
            return self.output

        return f"FAILED: {self.output}"
