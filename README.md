# Bitcoin Fork Monitor Website

This repo contains the source code for the https://btcforkmonitor.info

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

## License

This project is available under the MIT license. See the LICENSE file for more information.