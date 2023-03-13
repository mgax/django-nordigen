## Setup

```shell
pip install -r requirements.txt

# Replace with your Nordigen API credentials fromhttps://ob.nordigen.com/user-secrets/
export NORDIGEN_ID='...'
export NORDIGEN_KEY='...'
export NORDIGEN_SITE_URL='http://localhost:8000'

./manage.py migrate
DJANGO_SUPERUSER_PASSWORD=admin ./manage.py createsuperuser --username admin --noinput
```

## List institutions in a country

```shell
./manage.py nordigen_institutions RO
```

## Create a requisition

```shell
./manage.py nordigen_requisition SANDBOXFINANCE_SFIN0000
```

This prints a link to authorize the requisition: `https://ob.nordigen.com/psd2/start/...`. Click on the link and follow the process. In the meantime, start Django:

```shell
./manage.py runserver
```

The requisition process will eventually redirect back to Django and show "Nordigen requisition successful". Go to http://localhost:8000/admin/django_nordigen/requisition/ to see it.

## Sync transactions and balances

```shell
./manage.py nordigen_sync
```

Go to http://localhost:8000/admin/django_nordigen/account/ to see the syned data.

Note that the sandbox institution, `SANDBOXFINANCE_SFIN0000`, provides two accounts with a bunch of transactions, but none of them are _booked_, so django-nordigen ignores them.
