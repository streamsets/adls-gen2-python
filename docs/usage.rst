.. module:: downstage

Usage instructions
==================

The examples below assume you have installed the ``pip3 install git+https://github.com/streamsets/adls-gen2-python`` library,
and you are inside a Python 3.4+ interpreter.


And you have set the following environment variables:

* azure_tenant_id
* azure_client_id
* azure_client_secret

Getting Started
---------------
**Note:** In the following examples replace ``sample_account_name``, ``sample_filesystem``
with proper values that apply to your ADLS Gen 2.

Create an instance of :py:class:`downstage.AdlsGen2FileSystem`.

The following example shows to create an instance of :py:class:`downstage.OAuthAdlsFileSystem`:

    >>> from downstage import AdlsGen2FileSystem
    >>> gen2_fs = AdlsGen2FileSystem(authentication_method='Oauth2',
                                     account_name='sample_account_name',
                                     filesystem_id='sample_filesystem')

If ``create_filesystem=True`` is specified above, it creates the filesystem.
Otherwise, default is ``False`` and it assumes you have already created the filesystem.

Now you can create and manage directories inside it:

    >>> sample_directory = 'sample_directory'
    >>> gen2_fs.mkdir(sample_directory)
    >>> dl_files_command = gen2_fs.ls(sample_directory)
    >>> paths = dl_files_command.response.json()['paths']
    >>> names = [item['name'] for item in paths] if paths else []

And then you can create files in that directory and manage them:

    >>> file_name = 'sample_file'
    >>> path = '{}/{}'.format(sample_directory, file_name)
    >>> gen2_fs.touch(path)

Read and write to a file:

    >>> gen2_fs.write(path, 'Hello World!!')
    >>> contents = gen2_fs.cat(path).response.content.decode()


Lower-level API
---------------
**Note:** In the following examples replace ``sample_account_name``
with proper value that applies to your ADLS Gen 2.

If you want to use lower-level API, create an instance of :py:class:`downstage.AdlsGen2ApiClient`.

The following example shows to create an instance of :py:class:`downstage.OAuthAdlsGen2ApiClient`:


    >>> from downstage import AdlsGen2ApiClient
    >>> api_client = AdlsGen2ApiClient(authentication_method='Oauth2',
                                       account_name='sample_account_name')


Now you can create and manage directories inside it:

    >>> sample_filesystem = 'sample_filesystem'
    >>> sample_directory = 'sample_directory'
    >>> kwargs = {'resource': 'directory'}
    >>> headers = {"Content-Length": "0"}
    >>> api_client.create_path(sample_filesystem, directory_name, headers=headers, **kwargs)

And then you can create files in that directory and manage them:

    >>> file_name = 'sample_file'
    >>> path = '{}/{}'.format(sample_directory, file_name)
    >>> kwargs = {'resource': 'file'}
    >>> headers = {'Content-Length': '0', 'x-ms-version': '2018-11-09'}
    >>> api_client.create_path(sample_filesystem, path, headers=headers, **kwargs)

    >>> kwargs = {'directory': sample_directory}
    >>> list_directory_command = api_client.list_path(sample_filesystem, **kwargs)
    >>> list_directory_command.response.json()['paths']
