class ContractValidationError(ValueError):
    def __init__(self, message: str, line: int | None = None):
        self.line = line
        prefix = f"line {line}: " if line is not None else ""
        super().__init__(f"{prefix}{message}")


class ContractNotFoundError(FileNotFoundError):
    pass
