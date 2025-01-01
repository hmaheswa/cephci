import json

import requests

from utility.log import Log

LOG = Log(__name__)

# Constant for request URL verifier
DEFAULT_VERIFY = False


# Exception for status code `400`
class BadRequestError(Exception):
    pass


# Exception for status code `401`
class UnauthorizedError(Exception):
    pass


# Exception for status code `403`
class ForbiddenError(Exception):
    pass


# Exception for status code `500`
class InternalServerError(Exception):
    pass


class Api:
    """Interface for request API methods"""

    def __init__(self, url, api):
        # Disable insecure request warning in response
        requests.packages.urllib3.disable_warnings(
            requests.packages.urllib3.exceptions.InsecureRequestWarning
        )

        # Remove '/' from url and append with API
        self.url = f"{url.strip('/')}/{api}"

    def _response(self, response):
        """Validate request response

        Args:
            response (request.response) : Request response
        """
        if response.status_code == 400:
            raise BadRequestError(response.content)

        elif response.status_code == 401:
            raise UnauthorizedError(response.content)

        elif response.status_code == 403:
            raise ForbiddenError(response.content)

        elif response.status_code == 500:
            raise InternalServerError(response.content)

        return response.status_code, response.json()

    def get(
        self, data=None, header=None, auth=None, verify=DEFAULT_VERIFY, check_sc=False
    ):
        """Get method for request

        Args:
            data (dict): Request payload
            header (dict): Request header
            auth (tuple): Request authentication
            verify (bool): Request URL verifier
            check_sc (bool): Check for status code validation
        """
        LOG.info(f"Request URL - {self.url}")
        LOG.info(f"Request VERIFY - {verify}")
        LOG.info("Request METHOD - GET")

        params = {"url": self.url, "verify": verify}

        if data:
            params["data"] = json.dumps(data)
            LOG.debug(f"Request DATA - {data}")

        if header:
            params["headers"] = header
            LOG.info(f"Request HEADER - {header}")

        if auth:
            params["auth"] = auth
            LOG.info(f"Request AUTH - {auth}")

        response = requests.get(**params)
        if check_sc:
            return self._response(response)

        return response

    def post(
        self, data=None, header=None, auth=None, verify=DEFAULT_VERIFY, check_sc=False
    ):
        """Post method for request

        Args:
            data (dict): Request payload
            header (dict): Request header
            auth (tuple): Request authentication
            verify (bool): Request URL verifier
            check_sc (bool): Check for status code validation
        """
        LOG.info(f"Request URL - {self.url}")
        LOG.info(f"Request VERIFY - {verify}")
        LOG.info("Request METHOD - Post")

        params = {"url": self.url, "verify": verify}

        if data:
            params["data"] = json.dumps(data)
            LOG.debug(f"Request DATA - {data}")

        if header:
            params["headers"] = header
            LOG.info(f"Request HEADER - {header}")

        if auth:
            params["auth"] = auth
            LOG.info(f"Request AUTH - {auth}")

        response = requests.post(**params)
        if check_sc:
            return self._response(response)

        return response

    def put(self):
        pass

    def delete(
        self, data=None, header=None, auth=None, verify=DEFAULT_VERIFY, check_sc=False
    ):
        """Delete method for request

        Args:
            data (dict): Request payload
            header (dict): Request header
            auth (tuple): Request authentication
            verify (bool): Request URL verifier
            check_sc (bool): Check for status code validation
        """
        LOG.info(f"Request URL - {self.url}")
        LOG.info(f"Request VERIFY - {verify}")
        LOG.info("Request METHOD - Delete")

        params = {"url": self.url, "verify": verify}

        if data:
            params["data"] = json.dumps(data)
            LOG.debug(f"Request DATA - {data}")

        if header:
            params["headers"] = header
            LOG.info(f"Request HEADER - {header}")

        if auth:
            params["auth"] = auth
            LOG.info(f"Request AUTH - {auth}")

        response = requests.delete(**params)
        if check_sc:
            return self._response(response)

        return response

    def patch(
        self, data=None, header=None, auth=None, verify=DEFAULT_VERIFY, check_sc=False
    ):
        """Patch method for request

        Args:
            data (dict): Request payload
            header (dict): Request header
            auth (tuple): Request authentication
            verify (bool): Request URL verifier
            check_sc (bool): Check for status code validation
        """
        LOG.info(f"Request URL - {self.url}")
        LOG.info(f"Request VERIFY - {verify}")
        LOG.info("Request METHOD - Patch")

        params = {"url": self.url, "verify": verify}

        if data:
            params["data"] = json.dumps(data)
            LOG.debug(f"Request DATA - {data}")

        if header:
            params["headers"] = header
            LOG.info(f"Request HEADER - {header}")

        if auth:
            params["auth"] = auth
            LOG.info(f"Request AUTH - {auth}")

        response = requests.patch(**params)
        if check_sc:
            return self._response(response)

        return response
