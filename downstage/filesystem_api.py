#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Abstractions to interact with the ADLS Gen 2 REST API."""

import datetime
import json
import logging
import os
from abc import ABCMeta, abstractmethod

import requests

from downstage import constants
from .utils import get_params, join_url_parts

logger = logging.getLogger(__name__)

# Headers required to get an access token (after passing authentication_token to POST).
ACCESS_TOKEN_REQUIRED_HEADERS = {'content-Type': 'application/x-www-form-urlencoded'}
AUTH2_TOKEN_URL_TEMPLATE = 'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'

REQUIRED_HEADERS = {'content-type': 'application/json'}

HTTPS_BASE_URL = 'https://{account_name}.{dnssuffix}'


class AdlsGen2ApiClient:
    """A factory class used to create objects for ADLS Gen 2 API client.
    Underneath, each implementation might use a different method of authentication.

    Args:
        authentication_method (:obj:`str`): Type of authentication used. Valid values are: 'Oauth2' or 'SharedKey'
        account_name (:obj:`str`): ADLS Gen2 storage account name e.g. ``sandboxgen2``.
                                   Together with dns_suffix it forms the account FQDN.
                                   e.g. account FQDN = ``sandboxgen2.dfs.core.windows.net``
        dns_suffix (:obj:`str`): ADLS Gen2 dnssuffix e.g. ``dfs.core.windows.net``.
                                 Together with account_name it forms the account FQDN.
                                 e.g. account FQDN = ``sandboxgen2.dfs.core.windows.net``
                                 Default: ``dfs.core.windows.net``.
    """
    def __new__(cls, authentication_method, account_name, dns_suffix=constants.DEFAULT_DNS_SUFFIX):
        capitalized_authentication_method = authentication_method.upper()
        if capitalized_authentication_method == 'OAUTH2':
            client_id = os.environ.get('azure_client_id')  # Azure application id
            client_secret = os.environ.get('azure_client_secret')  # Azure application key
            tenant_id = os.environ.get('azure_tenant_id')  # Azure Active Directory's directory id
            if not all([client_id, client_secret, tenant_id]):
                raise ValueError('AdlsGen2ApiClient works only if all the following environment variables are set: '
                                 'azure_client_id, azure_client_secret and azure_tenant_id.')
            return OAuth2AdlsApiClient(account_name, dns_suffix, tenant_id, client_id, client_secret)
        else:
            raise ValueError(authentication_method)


class ApiClient(metaclass=ABCMeta):
    """
    API client to communicate with an ADLS Gen2 instance. This is an abstract class.
    """
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def _delete(self, url=None, endpoint=None, params=None, headers=None):
        pass

    @abstractmethod
    def _get(self, url=None, endpoint=None, params=None, headers=None):
        pass

    @abstractmethod
    def _head(self, url=None, endpoint=None, params=None, headers=None):
        pass

    @abstractmethod
    def _patch(self, url=None, endpoint=None, params=None, data=None, headers=None):
        pass

    @abstractmethod
    def _post(self, url=None, endpoint=None, params=None, data=None, files=None, headers=None,
              refresh_oauth2_token=True):
        pass

    @abstractmethod
    def _put(self, url=None, endpoint=None, params=None, data=None, headers=None):
        pass

    def _handle_http_error(self, response):
        # Delegating to response object error handling as last resort.
        try:
            response.raise_for_status()
        except:
            logger.error('Encountered an error while doing %s on %s. Response: %s',
                         response.request.method,
                         response.request.url,
                         response.__dict__)
            raise

    def list_filesystem(self, headers=None, **kwargs):
        """List filesystems and their properties in given account.

        https://docs.microsoft.com/en-us/rest/api/storageservices/datalakestoragegen2/filesystem/list
        lists the parameters available to be passed in kwargs.

        Args:
            headers (:obj:`dict`, optional): Request headers to pass. Default: ``None``.

        Returns:
            A :obj:`dict` of filesystem list and their properties.
        """
        logger.debug('Listing filesystem ...')
        resource = 'account'
        params = get_params(parameters=locals(), exclusions=['self', 'filesystem_identifier', 'headers'])
        response = self._get(params=params, headers=headers)
        return response.json() if response.content else {}

    def create_filesystem(self, filesystem_identifier, headers=None, **kwargs):
        """Create a filesystem rooted at the specified location.
        If the filesystem already exists, the operation fails.

        https://docs.microsoft.com/en-us/rest/api/storageservices/datalakestoragegen2/filesystem/create
        lists the parameters available to be passed in kwargs.

        Args:
            filesystem_identifier (:obj:`str`): The filesystem identifier
            headers (:obj:`dict`, optional): Request headers to pass. Default: ``None``.

        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        logger.debug('Creating filesystem %s ...', filesystem_identifier)
        resource = 'filesystem'
        params = get_params(parameters=locals(), exclusions=['self', 'filesystem_identifier', 'headers'])
        response = self._put(endpoint=filesystem_identifier, params=params, headers=headers)
        return Command(self, response)

    def delete_filesystem(self, filesystem_identifier, headers=None, **kwargs):
        """Marks the filesystem for deletion.

        https://docs.microsoft.com/en-us/rest/api/storageservices/datalakestoragegen2/filesystem/delete
        lists the parameters available to be passed in kwargs.

        Args:
            filesystem_identifier (:obj:`str`): The filesystem identifier
            headers (:obj:`dict`, optional): Request headers to pass. Default: ``None``.

        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        logger.debug('Deleting filesystem %s ...', filesystem_identifier)
        resource = 'filesystem'
        params = get_params(parameters=locals(), exclusions=['self', 'filesystem_identifier', 'headers'])
        response = self._delete(endpoint=filesystem_identifier, params=params, headers=headers)
        return Command(self, response)

    def get_filesystem_properties(self, filesystem_identifier, headers=None, **kwargs):
        """Get Filesystem Properties.

        https://docs.microsoft.com/en-us/rest/api/storageservices/datalakestoragegen2/filesystem/getproperties
        lists the parameters available to be passed in kwargs.

        Args:
            filesystem_identifier (:obj:`str`): The filesystem identifier
            headers (:obj:`dict`, optional): Request headers to pass. Default: ``None``.

        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        logger.debug('Getting properties for filesystem %s ...', filesystem_identifier)
        resource = 'filesystem'
        params = get_params(parameters=locals(), exclusions=['self', 'filesystem_identifier', 'headers'])
        response = self._head(endpoint=filesystem_identifier, params=params, headers=headers)
        return Command(self, response)

    def set_filesystem_properties(self, filesystem_identifier, headers=None, **kwargs):
        """Set Filesystem Properties.

        https://docs.microsoft.com/en-us/rest/api/storageservices/datalakestoragegen2/filesystem/setproperties
        lists the parameters available to be passed in kwargs.

        Args:
            filesystem_identifier (:obj:`str`): The filesystem identifier
            headers (:obj:`dict`, optional): Request headers to pass. Default: ``None``.

        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        logger.debug('Setting properties for filesystem %s ...', filesystem_identifier)
        resource = 'filesystem'
        params = get_params(parameters=locals(), exclusions=['self', 'filesystem_identifier', 'headers'])
        response = self._patch(endpoint=filesystem_identifier, params=params, headers=headers)
        return Command(self, response)

    def create_path(self, filesystem_identifier, path, headers=None, **kwargs):
        """Create File | Create Directory | Rename File | Rename Directory.

        https://docs.microsoft.com/en-us/rest/api/storageservices/datalakestoragegen2/path/create
        lists the parameters available to be passed in kwargs.

        Args:
            filesystem_identifier (:obj:`str`): The filesystem identifier
            path (:obj:`str`): The path to be created. e.g. directory_name.
            headers (:obj:`dict`, optional): Request headers to pass. Default: ``None``.

        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        logger.debug('Creating path %s/%s...', filesystem_identifier, path)
        params = get_params(parameters=locals(), exclusions=['self', 'filesystem_identifier', 'path', 'headers'])
        response = self._put(endpoint='{}/{}'.format(filesystem_identifier, path),
                             params=params,
                             headers=headers)
        return Command(self, response)

    def delete_path(self, filesystem_identifier, path, recursive=True, headers=None, **kwargs):
        """Delete File | Delete Directory.

        https://docs.microsoft.com/en-us/rest/api/storageservices/datalakestoragegen2/path/delete
        lists the parameters available to be passed in kwargs.

        Args:
            filesystem_identifier (:obj:`str`): The filesystem identifier
            path (:obj:`str`): The file or directory path.
            recursive (:obj:`boolean`, optional): valid only when the resource is a directory.
                                                  If ``True``, all paths beneath the directory will be deleted.
                                                  Default: ``True``.
                                                  If ``False`` and the directory is non-empty, an error occurs.
            headers (:obj:`dict`, optional): Request headers to pass. Default: ``None``.

        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        logger.debug('Deleting path %s/%s...', filesystem_identifier, path)
        params = get_params(parameters=locals(), exclusions=['self', 'filesystem_identifier', 'path', 'headers'])
        response = self._delete(endpoint='{}/{}'.format(filesystem_identifier, path),
                                params=params,
                                headers=headers)
        return Command(self, response)

    def list_path(self, filesystem_identifier, recursive=True, headers=None, **kwargs):
        """List filesystem paths and their properties.

        https://docs.microsoft.com/en-us/rest/api/storageservices/datalakestoragegen2/path/list
        lists the parameters available to be passed in kwargs.

        Args:
            filesystem_identifier (:obj:`str`): The filesystem identifier
            recursive (:obj:`boolean`, optional): If ``True``, all paths are listed;
                                                  otherwise, only paths at the root of the filesystem are listed.
                                                  Default: ``True``.
            headers (:obj:`dict`, optional): Request headers to pass. Default: ``None``.

        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        logger.debug('Listing path %s ...', filesystem_identifier)
        resource = 'filesystem'
        params = get_params(parameters=locals(), exclusions=['self', 'filesystem_identifier', 'headers'])
        response = self._get(endpoint=filesystem_identifier,
                             params=params,
                             headers=headers)
        return Command(self, response)

    def read_path(self, filesystem_identifier, path, headers=None, **kwargs):
        """Read File. Read the contents of a file.

        https://docs.microsoft.com/en-us/rest/api/storageservices/datalakestoragegen2/path/read
        lists the parameters available to be passed in kwargs.

        Args:
            filesystem_identifier (:obj:`str`): The filesystem identifier
            path (:obj:`str`): The file or directory path.
            headers (:obj:`dict`, optional): Request headers to pass. Default: ``None``.

        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        logger.debug('Reading path %s/%s...', filesystem_identifier, path)
        params = get_params(parameters=locals(), exclusions=['self', 'filesystem_identifier', 'path', 'headers'])
        response = self._get(endpoint='{}/{}'.format(filesystem_identifier, path),
                             params=params,
                             headers=headers)
        return Command(self, response)

    def update_path(self, filesystem_identifier, path, data=None, headers=None, **kwargs):
        """Append Data | Flush Data | Set Properties | Set Access Control
        Uploads data to be appended to a file, flushes (writes) previously uploaded data to a file,
        sets properties for a file or directory, or sets access control for a file or directory.

        https://docs.microsoft.com/en-us/rest/api/storageservices/datalakestoragegen2/path/update
        lists the parameters available to be passed in kwargs.

        Args:
            filesystem_identifier (:obj:`str`): The filesystem identifier
            path (:obj:`str`): The file or directory path.
            data (:obj:`str`, optional): Contents. Default: ``None``.
            headers (:obj:`dict`, optional): Request headers to pass. Default: ``None``.

        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        logger.debug('Updating path %s/%s...', filesystem_identifier, path)
        params = get_params(parameters=locals(), exclusions=['self', 'filesystem_identifier', 'pat', 'data','headers'])
        response = self._patch(endpoint='{}/{}'.format(filesystem_identifier, path),
                               params=params,
                               data=data,
                               headers=headers)
        return Command(self, response)

    def get_path_properties(self, filesystem_identifier, path, headers=None, **kwargs):
        """Get Properties | Get Status | Get Access Control List
        Get Properties returns all system and user defined properties for a path.
        Get Status returns all system defined properties for a path.
        Get Access Control List returns the access control list for a path.

        https://docs.microsoft.com/en-us/rest/api/storageservices/datalakestoragegen2/path/getproperties
        lists the parameters available to be passed in kwargs.

        Args:
            filesystem_identifier (:obj:`str`): The filesystem identifier
            path (:obj:`str`): The file or directory path.
            headers (:obj:`dict`, optional): Request headers to pass. Default: ``None``.

        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        logger.debug('Getting properties for path %s/%s...', filesystem_identifier, path)
        params = get_params(parameters=locals(), exclusions=['self', 'filesystem_identifier', 'path', 'headers'])
        response = self._head(endpoint='{}/{}'.format(filesystem_identifier, path),
                              params=params,
                              headers=headers)
        return Command(self, response)

    def lease_path(self, filesystem_identifier, path, headers=None, **kwargs):
        """Lease Path
        Create and manage a lease to restrict write and delete access to the path.

        https://docs.microsoft.com/en-us/rest/api/storageservices/datalakestoragegen2/path/lease
        lists the parameters available to be passed in kwargs.

        Args:
            filesystem_identifier (:obj:`str`): The filesystem identifier
            path (:obj:`str`): The file or directory path.
            headers (:obj:`dict`, optional): Request headers to pass. Default: ``None``.
                                             x-ms-lease-action is a required header.

        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        logger.debug('Leasing path %s/%s...', filesystem_identifier, path)
        params = get_params(parameters=locals(), exclusions=['self', 'filesystem_identifier', 'path', 'headers'])
        response = self._post(endpoint='{}/{}'.format(filesystem_identifier, path),
                              params=params,
                              headers=headers)
        return Command(self, response)


class OAuth2AdlsApiClient(ApiClient):
    """
    API client to communicate with an ADLS Gen2 instance.
    Fetches access token which is required for all other requests sent to the ADLS Gen2.
    Running this endpoint will set the ``Authorization`` session header for this ApiClient instance.

    Args:
        account_name (:obj:`str`): ADLS Gen2 storage account name e.g. ``sandboxgen2``.
                                   Together with dns_suffix it forms the account FQDN.
                                   e.g. account FQDN = ``sandboxgen2.dfs.core.windows.net``
        dns_suffix (:obj:`str`): ADLS Gen2 dns_suffix e.g. ``dfs.core.windows.net``.
                                 Together with account_name it forms the account FQDN.
                                 e.g. account FQDN = ``sandboxgen2.dfs.core.windows.net``
        tenant_id (:obj:`str`): The tenant id for ADLS Gen2.
        client_id (:obj:`int`): The client id for ADLS Gen2.
        client_secret (:obj:`str`): The client secret for ADLS Gen2
    """
    def __init__(self,
                 account_name,
                 dns_suffix,
                 tenant_id,
                 client_id,
                 client_secret):
        self._account_name = account_name
        self._dns_suffix = dns_suffix
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = HTTPS_BASE_URL.format(account_name=account_name, dnssuffix=dns_suffix)

        self.session = requests.Session()
        self._oauth2_token_time_expiration = None

        self.refresh_oauth2_token_command = Command(self, self._refresh_oauth2_token())

    # Internal functions only below.
    def _refresh_oauth2_token(self):
        # Since oauth2 access_token expires after expires_in no. of seconds, we check if the token has
        # elapsed the expiry time and if it did, then we refresh the oauth2 token and there by extend its lapse time.
        time_until_expiration = ((self._oauth2_token_time_expiration - datetime.datetime.now())
                                 if self._oauth2_token_time_expiration else None)
        data = ('scope=https://storage.azure.com/.default&grant_type=client_credentials'
                '&client_id={}&client_secret={}'.format(self._client_id, self._client_secret))
        if not time_until_expiration or time_until_expiration.total_seconds() < 0:  # token expired
            response = self._post(url=AUTH2_TOKEN_URL_TEMPLATE.format(tenant_id=self._tenant_id),
                                  data=data,
                                  headers=ACCESS_TOKEN_REQUIRED_HEADERS,
                                  refresh_oauth2_token=False)
            self._handle_http_error(response)
            self.session.headers.update(REQUIRED_HEADERS)
            self.session.headers['Authorization'] = 'Bearer {}'.format(response.json()['access_token'])
            # 45 seconds is deducted for network and server response latency
            token_expires_from_now_secs = response.json()['expires_in'] - 45
            self._oauth2_token_time_expiration = (datetime.datetime.now() +
                                                  datetime.timedelta(seconds=token_expires_from_now_secs))
            return response

    def _delete(self, url=None, endpoint=None, params=None, headers=None):
        self._refresh_oauth2_token()
        url = self._base_url if url is None else url
        if endpoint:
            url = join_url_parts(url, endpoint)
        logger.debug('Sending DELETE request with url=%s, headers=%s, params=%s', url, headers, params)
        response = self.session.delete(url, params=params or {}, headers=headers)
        self._handle_http_error(response)
        return response

    def _get(self, url=None, endpoint=None, params=None, headers=None):
        self._refresh_oauth2_token()
        url = self._base_url if url is None else url
        if endpoint:
            url = join_url_parts(url, endpoint)
        logger.debug('Sending GET request with url=%s, headers=%s, params=%s', url, headers, params)
        response = self.session.get(url, params=params or {}, headers=headers)
        self._handle_http_error(response)
        return response

    def _head(self, url=None, endpoint=None, params=None, headers=None):
        self._refresh_oauth2_token()
        url = self._base_url if url is None else url
        if endpoint:
            url = join_url_parts(url, endpoint)
        logger.debug('Sending HEAD request with url=%s, headers=%s, params=%s', url, headers, params)
        response = self.session.head(url, params=params or {}, headers=headers)
        self._handle_http_error(response)
        return response

    def _patch(self, url=None, endpoint=None, params=None, data=None, headers=None):
        self._refresh_oauth2_token()
        url = self._base_url if url is None else url
        if endpoint:
            url = join_url_parts(url, endpoint)
        if data and not isinstance(data, str):
            data = json.dumps(data)
        logger.debug('Sending PATCH request with url=%s, headers=%s, params=%s', url, headers, params)
        response = self.session.patch(url, params=params or {}, data=data, headers=headers)
        self._handle_http_error(response)
        return response

    def _post(self, url=None, endpoint=None, params=None, data=None, files=None, headers=None,
              refresh_oauth2_token=True):
        if refresh_oauth2_token:
            self._refresh_oauth2_token()
        url = self._base_url if url is None else url
        if endpoint:
            url = join_url_parts(url, endpoint)
        if data and not isinstance(data, str):
            data = json.dumps(data)
        logger.debug('Sending POST request with url=%s, headers=%s, params=%s', url, headers, params)
        response = self.session.post(url, params=params or {}, data=data, files=files, headers=headers)
        self._handle_http_error(response)
        return response

    def _put(self, url=None, endpoint=None, params=None, data=None, headers=None):
        self._refresh_oauth2_token()
        url = self._base_url if url is None else url
        if endpoint:
            url = join_url_parts(url, endpoint)
        if data and not isinstance(data, str):
            data = json.dumps(data)
        logger.debug('Sending PUT request with url=%s, headers=%s, params=%s', url, headers, params)
        response = self.session.put(url, params=params or {}, data=data, headers=headers)
        self._handle_http_error(response)
        return response


class Command:
    """Command to allow users to interact with commands submitted through ADLS Gen2 REST API.

    Args:
        api_client (:obj:`ApiClient`): ADLS Gen2 API client.
        response (:obj:`requests.Response`): Command reponse.
    """
    def __init__(self, api_client, response):
        self.api_client = api_client
        self.response = response
