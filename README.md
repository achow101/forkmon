# Bitcoin Fork Monitor Website

This repo contains the source code for the https://www.btcforkmonitor.info

## Building and testing locally

Install Python 3. Install all of the dependencies in the requirements.txt
file.

For testing and debugging purposes, it may be easier to replace the lines
in settings about the `DATABASES` with the following:

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

### Running

The first time you run this software, you will need to do some database
preparation and setup. You will need to run the following commands first:

    python manage.py makemigrations
    python manage.py migrate
    python manage.py createsuperuser

Then you can run the website with

    python manage.py runserver

The website will be available at http://127.0.0.1:8000. The administration
panel is available at http://127.0.0.1:8000/admin

The first time you run this, you will need to login to the admin panel and add
some nodes, one block for each node, and the initial fork state.

### Developing

Run the website with

    python manage.py runserver

Any changes made to any of the file in this project will be automatically updated
and reflected in the website by refreshing the web page.

### Updating information from nodes

To update information from the nodes, you will need to specify `RPC_USER` and `RPC_PASSWORD`
environment variables. These should match the `rpcuser` and `rpcpassword` that you have specified
for your nodes. THe `rpcuser` and `rpcpassword` must be the same for all nodes. To update
the database, run the following command:

    python manage.py node_updates

### modifying the updater

The updater command's logic is defined in [`monitor/node_updates.py`](monitor/node_updates.py).

## License

This project is available under the MIT license. See the LICENSE file for more information.