from core.models import Response


def success(message, source="system", data=None):
    return Response(
        success=True,
        message=message,
        source=source,
        response_type="reply",
        data=data,
    )


def error(message, source="system"):
    return Response(
        success=False,
        message=message,
        source=source,
        response_type="error",
    )


def info(message, source="system", data=None):
    return Response(
        success=True,
        message=message,
        source=source,
        response_type="info",
        data=data,
    )
