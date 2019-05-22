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

import pytest

from downstage import AdlsGen2ApiClient, AdlsGen2FileSystem, constants


def pytest_addoption(parser):
    """Hook that defines custom command line options to be passed to pytest."""
    parser.addoption('--account-name', help='ADLS Gen2 account name e.g. ``sandboxgen2``')
    parser.addoption('--dns-suffix', help='ADLS Gen2 dns suffix e.g. ``dfs.core.net``',
                     default=constants.DEFAULT_DNS_SUFFIX)
    parser.addoption('--create-filesystem', action='store_true',
                     help='Create filesystem.')
    parser.addoption('--filesystem-id', help='ADLS Gen2 filesystem identifier')


@pytest.fixture(scope='session')
def args():
    """A session-level ``args`` fixture for test functions.
    We provide an object with command line arguments as attributes. This is done to be consistent
    with the behavior of argparse.
    """
    # pytest's Config class stores a dictionary of argparse argument name => dest. Go through this
    # dictionary and return back an args object whose attributes map dest to its option value.
    pytest_args = {arg: pytest.config.getoption(arg)
                   for arg in pytest.config._opt2dest.values()}
    return type('args', (object,), pytest_args)


@pytest.fixture(scope='session')
def adls_gen2_fs_oauth2_api_client(args):
    """Fixture that returns the ADLSGen2APIClient instance's api_cleint.
    This particular fixture uses Oauth2 authentication method.
    Useful for testing the underlying filesystem_api."""
    if not args.account_name:
        raise Exception('Test runs only if --account-name is passed.')
    return AdlsGen2ApiClient(authentication_method='Oauth2', account_name=args.account_name)


@pytest.fixture(scope='session')
def adls_gen2_fs_oauth2(args):
    """Fixture that returns the ADLSGen2FileSystem instance's api_cleint.
    This particular fixture uses Oauth authentication method.
    Useful for testing the underlying filesystem_api."""
    if not all([args.account_name, args.filesystem_id]):
        raise Exception('Test runs only if --account-name and --filesystem-id are passed.')
    return AdlsGen2FileSystem(authentication_method='Oauth2',
                              account_name=args.account_name,
                              filesystem_id=args.filesystem_id,
                              create=args.create_filesystem,
                              dns_suffix=args.dns_suffix)
