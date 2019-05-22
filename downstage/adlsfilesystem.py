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

"""Abstractions for interacting with ADLS Gen2."""

import logging
import os
from abc import ABCMeta, abstractmethod

from downstage import filesystem_api, constants

logger = logging.getLogger(__name__)

class AdlsGen2FileSystem:
    """A factory class used to create objects for ADLS Gen 2 File System.
    Underneath, each implementation might use a different method of authentication.

    Args:
        authentication_method (:obj:`str`): Type of authentication used. Valid values are: 'Oauth2' or 'SharedKey'
        account_name (:obj:`str`): ADLS Gen2 storage account name e.g. ``sandboxgen2``.
                                   Together with dns_suffix it forms the account FQDN. Default: ``dfs.core.windows.net``
                                   e.g. account FQDN = ``sandboxgen2.dfs.core.windows.net``
        filesystem_id (:obj:`str`): ADLS Gen2 filesystem identifier.
        create (:obj:`boolean`, optional): If True, create the file system, otherwise it exists.
                                           Default: ``False``.
        dns_suffix (:obj:`str`): ADLS Gen2 dns_suffix e.g. ``dfs.core.windows.net``.
                                 Together with account_name it forms the account FQDN.
                                 e.g. account FQDN = ``sandboxgen2.dfs.core.windows.net``
    """
    def __new__(cls, authentication_method, account_name,
                filesystem_id, create=False, dns_suffix=constants.DEFAULT_DNS_SUFFIX):
        capitalized_authentication_method = authentication_method.upper()
        if capitalized_authentication_method == 'OAUTH2':
            client_id = os.environ.get('azure_client_id')  # Azure application id
            client_secret = os.environ.get('azure_client_secret')  # Azure application key
            tenant_id = os.environ.get('azure_tenant_id')  # Azure Active Directory's directory id
            if not all([client_id, client_secret, tenant_id]):
                raise ValueError('AdlsGen2FileSystem works only if all the following environment variables are set: '
                                 'azure_client_id, azure_client_secret and azure_tenant_id.')
            return OAuth2AdlsFileSystem(account_name, dns_suffix,
                                        tenant_id, client_id, client_secret,
                                        filesystem_id, create)
        else:
            raise ValueError(authentication_method)


class AdlsFileSystem(metaclass=ABCMeta):
    """Class to interact with ADLS Gen2. This is an abstract class.

    Args:
        filesystem_id (:obj:`str`): ADLS Gen2 filesystem identifier.
        create (:obj:`boolean`, optional): If True, create the file system, otherwise it exists.
                                           Default: ``False``.
    """

    @abstractmethod
    def __init__(self, filesystem_id, create=False):
        self.filesystem_id = filesystem_id
        # Specifies the version of the REST protocol used for processing the request.
        self.headers = {'x-ms-version': '2018-11-09'}
        if create:
            # Create a filesystem rooted at the specified location.
            self.api_client.create_filesystem(filesystem_id, self.headers)

    def mkdir(self, path):
        """Create Directory.

        Args:
            path (:obj:`str`): The path to be created. e.g. name of directory.
        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        kwargs = {'resource': 'directory'}
        headers = {'Content-Length': '0'}
        headers.update(self.headers)
        return self.api_client.create_path(self.filesystem_id, path, headers, **kwargs)

    def touch(self, path):
        """Create an empty file.

        Args:
            path (:obj:`str`): The path to be created. e.g. name of file.
        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        kwargs = {'resource': 'file'}
        headers = {'Content-Length': '0'}
        headers.update(self.headers)
        return self.api_client.create_path(self.filesystem_id, path, headers, **kwargs)

    def rmdir(self, path, recursive=True):
        """Delete a directory.

        Args:
            path (:obj:`str`): The path to be deleted. e.g. directory_name.
            recursive (:obj:`boolean`, optional): If ``True``, all paths beneath the directory will be deleted.
                                                  Default: ``True``.
                                                  If ``False`` and the directory is non-empty, an error occurs.
        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        return self.api_client.delete_path(self.filesystem_id, path, recursive, self.headers)

    def rm(self, path):
        """Delete a file.

        Args:
            path (:obj:`str`): The path to be deleted. e.g. directory_name/file_name.

        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        return self.api_client.delete_path(self.filesystem_id, path, False, self.headers)

    def ls(self, path, recursive=False):
        """List contents of a directory.

        Args:
            path (:obj:`str`): The path. e.g. directory_name.
            recursive (:obj:`boolean`, optional): If ``True``, all paths beneath the directory will be listed.
                                                  Default: ``False``.
        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        kwargs = {'directory': path}
        return self.api_client.list_path(self.filesystem_id, recursive, self.headers, **kwargs)

    def cat(self, path):
        """List contents of a file.

        Args:
            path (:obj:`str`): The path. e.g. directory_name/file_name.
        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        return self.api_client.read_path(self.filesystem_id, path, self.headers)

    def write(self, path, contents, content_type='text/plain', position=0):
        """Upload contents and after that, flush (write) previously uploaded contents
        to a file starting at position.

        Args:
            path (:obj:`str`): The path. e.g. directory_name/file_name.
            contents (:obj:): The contents to be written.
            content_type (:obj:`str`): The content_type. Default ``text/plain``
            position (:obj:`int`): The position at which to start writing contents in the file.
        Returns:
            An instance of :py:class:`downstage.filesystem_api.Command`
        """
        contents_length = len(contents)

        # Append contents.
        kwargs = {'action': 'append', 'position': position}
        headers = {'Content-Length': str(contents_length)}
        headers.update(self.headers)
        self.api_client.update_path(self.filesystem_id, path, contents, headers, **kwargs)

        # After the append operation, the text sits in an uncommitted buffer on the server.
        # To send buffered data to the file system, flush the contents.
        kwargs = {'action': 'flush', 'position': position + contents_length}
        headers = {'Content-Length': '0', 'x-ms-content-type': content_type}
        headers.update(self.headers)
        return self.api_client.update_path(self.filesystem_id, path, headers=headers, **kwargs)


class OAuth2AdlsFileSystem(AdlsFileSystem):
    """Class to interact with ADLS Gen2 using OAuth2 mechanism.

    Args:
        account_name (:obj:`str`): ADLS Gen2 storage account name e.g. ``sandboxgen2``.
                                   Together with dns_suffix it forms the account FQDN.
                                   e.g. account FQDN = ``sandboxgen2.dfs.core.windows.net``
        dns_suffix (:obj:`str`): ADLS Gen2 dns_suffix e.g. ``dfs.core.windows.net``.
                                 Together with account_name it forms the account FQDN.
                                 e.g. account FQDN = ``sandboxgen2.dfs.core.windows.net``
        tenant_id (:obj:`str`): ADLS Gen2 tenant id.
        client_id (:obj:`str`): ADLS Gen2 client id.
        client_secret (:obj:`str`): ADLS Gen2 client secret.
        filesystem_id (:obj:`str`): ADLS Gen2 filesystem identifier.
        create (:obj:`boolean`, optional): If ``True``, create the file system, otherwise it exists.
                                           Default: ``False``.
    """

    def __init__(self,
                 account_name,
                 dns_suffix,
                 tenant_id,
                 client_id,
                 client_secret,
                 filesystem_id,
                 create=False):
        self.api_client = filesystem_api.OAuth2AdlsApiClient(account_name=account_name,
                                                             dns_suffix=dns_suffix,
                                                             tenant_id=tenant_id,
                                                             client_id=client_id,
                                                             client_secret=client_secret)
        super().__init__(filesystem_id, create)
