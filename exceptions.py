class APIResponseException(Exception):
    """Exception to check API response for correctness."""

    pass


class StatusException(Exception):
    """Exception to check the status in the API response."""

    pass


class GetAPIException(Exception):
    """Exception to check the API request."""

    pass


class SendMessageException(Exception):
    """Exception to check message sending."""

    pass


class VariableException(Exception):
    """Exception to check for environment variables."""

    pass


class RequestException(Exception):
    """Exception to check the request."""

    pass
