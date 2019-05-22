.. readme-start

Usage instructions
==================

The examples below assume you have installed the ``pip3 install git+https://github.com/streamsets/adls-gen2-python`` library,
and you have pytest installed.

Currently tests are run with pytest version 3.9.3.

And you have to set the following environment variables:

* azure_client_id
* azure_client_secret
* azure_tenant_id

To run the tests
================
**Note:** In the following examples replace ``sample_account_name``, ``sample_filesystem``
with proper values that apply to your ADLS Gen 2.

Clone the repo from https://github.com/streamsets/adls-gen2-python

cd ${REPO_DIRECTORY} where REPO_DIRECTORY is the directory where the above repo was cloned.

>>>  pytest -v --account-name 'sample_account_name' --filesystem-id 'sample_filesystem' tests/test_filesystem_object.py

To run above tests with debug statements:

>>>  pytest  --log-level DEBUG -s --account-name 'sample_account_name' --filesystem-id 'sample_filesystem' tests/test_filesystem_object.py

**Low-level API tests:**

>>>  pytest -v --account-name 'sample_account_name' tests/test_path_with_api_client.py
>>>  pytest -v --account-name 'sample_account_name' tests/test_filesystem_with_api_client.py

To run above tests with debug statements:

>>> pytest  --log-level DEBUG -s --account-name 'sample_account_name' tests/test_path_with_api_client.py
>>> pytest  --log-level DEBUG -s --account-name 'sample_account_name' tests/test_filesystem_with_api_client.py


.. readme-end
