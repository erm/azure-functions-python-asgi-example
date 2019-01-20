import enum
import asyncio
import urllib.parse


class ASGICycleState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()


class ASGIHTTPCycle:
    def __init__(self, scope: dict, loop: asyncio.AbstractEventLoop) -> None:

        self.scope = scope
        self.app_queue = asyncio.Queue(loop=loop)
        self.state = ASGICycleState.REQUEST
        self.response = {}

    def put_message(self, message: dict) -> None:
        self.app_queue.put_nowait(message)

    async def receive(self) -> dict:
        message = await self.app_queue.get()
        return message

    async def send(self, message: dict) -> None:
        message_type = message["type"]

        if self.state is ASGICycleState.REQUEST:
            if message_type != "http.response.start":
                raise RuntimeError(
                    f"Expected 'http.response.start', received: {message_type}"
                )

            status_code = message["status"]
            # headers = message.get("headers", [])

            self.response["status_code"] = status_code
            self.state = ASGICycleState.RESPONSE

        elif self.state is ASGICycleState.RESPONSE:
            if message_type != "http.response.body":
                raise RuntimeError(
                    f"Expected 'http.response.body', received: {message_type}"
                )
            body = message["body"]
            if isinstance(body, bytes):
                body = body.decode("utf-8")
            self.response["body"] = body

            self.put_message({"type": "http.disconnect"})


def asgi_handler(app, req) -> dict:
    server = None
    client = None
    scheme = "https"

    if req.params:
        query_string = urllib.parse.urlencode(req.params).encode("ascii")
    else:
        query_string = ""

    scope = {
        "type": "http",
        "server": server,
        "client": client,
        "method": req.method,
        "path": req.params["uri"],
        "scheme": scheme,
        "http_version": "1.1",
        "root_path": "",
        "query_string": query_string,
        "headers": req.headers.items(),
    }

    body = b""
    more_body = False

    loop = asyncio.new_event_loop()
    asgi_cycle = ASGIHTTPCycle(scope, loop=loop)
    asgi_cycle.put_message(
        {"type": "http.request", "body": body, "more_body": more_body}
    )
    asgi_instance = app(asgi_cycle.scope)
    asgi_task = loop.create_task(asgi_instance(asgi_cycle.receive, asgi_cycle.send))
    loop.run_until_complete(asgi_task)

    return asgi_cycle.response
