class DomainError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class PermissionDeniedError(DomainError):
    pass


class AuthenticationError(DomainError):
    pass


class InvalidInputError(DomainError):
    pass
