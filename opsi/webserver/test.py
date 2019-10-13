import logging

LOGGER = logging.getLogger(__name__)


class WebserverTest:
    def __init__(self, app):
        self.app = app
        self.client = None

    def _ensure_client(self):
        if self.client is None:
            # Importing this requires requests
            # Since this is only for testing,
            # don't require dependency unless used

            try:
                from starlette.testclient import TestClient
            except ModuleNotFoundError:
                LOGGER.exception("Requests module needed for WebserverTest")
                raise

            self.client = TestClient(self.app)

    def request(self, method, path, data=None) -> str:
        self._ensure_client()

        args = {"method": method, "url": path}

        if method == "GET":
            data = None
            args["allow_redirects"] = True

        args["data"] = data

        response = self.client.request(**args)
        response.raise_for_status()  # raise error on 4xx or 5xx

        return response.text

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, data=None):
        return self.request("POST", path, data)
