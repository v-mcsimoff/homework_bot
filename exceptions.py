class APIResponseException(Exception):
    """Исключение для проверки ответа API на корректность."""

    pass


class StatusException(Exception):
    """Исключение для проверки статуса в ответе API."""

    pass


class GetAPIException(Exception):
    """Исключение для проверки запроса к API."""

    pass


class SendMessageException(Exception):
    """Исключение для проверки отправки сообщений."""

    pass


class VariableException(Exception):
    """Исключение для проверки наличия переменных окружения."""

    pass
