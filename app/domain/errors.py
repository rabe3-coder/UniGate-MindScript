"""Typed application failures mapped into HTTP at the boundary."""
class AppError(Exception):
    def __init__(self, message, status=400, code='VALIDATION'):
        super().__init__(message)
        self.status, self.code = status, code

