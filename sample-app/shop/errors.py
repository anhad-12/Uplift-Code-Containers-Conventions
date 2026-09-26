class ShopError(Exception):
    """Base class for all domain errors."""


class NotFoundError(ShopError):
    def __init__(self, resource: str, key) -> None:
        super().__init__(f"{resource} {key} not found")
        self.resource = resource
        self.key = key


class ValidationError(ShopError):
    pass
