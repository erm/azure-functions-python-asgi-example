import logging

import azure.functions as func
from .asgi import asgi_handler
from .app import App


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")
    response = asgi_handler(App, req)
    return func.HttpResponse(response["body"], status_code=response["status_code"])
