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

import logging
import random

from inflection import camelize

logger = logging.getLogger(__name__)


def get_random_string(characters, length=8):
    """
    Returns a string of the requested length consisting of random combinations of the given
    sequence of string characters.
    """
    return ''.join(random.choice(characters) for _ in range(length))


def join_url_parts(*parts):
    """
    Join a URL from a list of parts. See http://stackoverflow.com/questions/24814657 for
    examples of why urllib.parse.urljoin is insufficient for what we want to do.
    """
    return '/'.join([piece.strip('/') for piece in parts])


def get_params(parameters, exclusions=None, process_kwargs=True):
    """Get a dictionary of parameters to be passed as requests methods' params argument.

    The typical use of this method is to pass in locals() from a function that wraps a
    REST endpoint. It will then create a dictionary, filtering out any exclusions (e.g.
    path parameters) and unset parameters, and use camelize to convert arguments from
    ``this_style`` to ``thisStyle``.

    Args:
        parameters (:obj:`dict`): Key-worded arguments to be passed.
        exclusions (:obj:`list`, optional): Optional list of exclusions.
        process_kwargs (:obj:`boolean`, optional): If True, only the value of them is kept.
                                                   e.g. if kwargs = {'key1': 'value1'} will be passed instead of
                                                   {'kwargs': {'key1': 'value1'}}
    """
    if process_kwargs:
        passed_kwargs = parameters.get('kwargs', None)
        if passed_kwargs is not None:
            parameters.update({key: value for key, value in passed_kwargs.items()})
            parameters.pop('kwargs')
    return {camelize(arg, uppercase_first_letter=False): value
            for arg, value in parameters.items()
            if value is not None and arg not in exclusions}
