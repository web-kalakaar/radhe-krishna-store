# Radhe Krishna Store

An online store for a single shop, built with Django. Customers browse products by category, add them to a cart and place Cash on Delivery orders. The owner manages orders, stock and products from a separate panel.

> Portfolio project. OTP runs in demo mode (see [Notes](#notes)).

## Features

### Customer

- Products grouped by category, with search, price range filter, sorting and pagination
- Amazon-style prices: MRP crossed out, selling price and discount percentage
- Product page with a photo gallery, key features table and stock status
- Sign up and log in, with a saved mobile number and multiple saved addresses
- Cart with live item count, Cash on Delivery checkout, mobile OTP verification
- "My orders" page with order details, delivery contact and order cancellation

### Owner (separate panel at `/owner/`)

- Overview: new orders, low stock and out-of-stock products
- Orders: filter by status, enter delivery person details, mark delivered or cancel
- Stock: record offline sales, restocks and count corrections, with a full history log
- Products: add and edit products with photos and key features

## Tech stack

- Python 3.13, Django 5.2 (LTS)
- SQLite (development)
- HTML, CSS and a little JavaScript
- Pillow (image uploads), python-decouple (environment variables)

## Getting started

```bash
git clone https://github.com/web-kalakaar/radhe-krishna-store.git
cd radhe-krishna-store

python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate

pip install -r requirements.txt

copy .env.example .env         # Mac/Linux: cp .env.example .env
```

Open `.env` and set a real secret key. Generate one with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Then set up the database and demo data:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py runserver
```

- Shop: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Owner panel: [http://127.0.0.1:8000/owner/](http://127.0.0.1:8000/owner/) (log in with the superuser account)
- Django admin: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

`seed_demo` creates demo categories and 24 products with generated placeholder photos. It is safe to run more than once.

## Running the tests

```bash
python manage.py test
```

The tests cover the rules that matter most: price calculation, stock changes, placing and cancelling orders, the OTP rules (expiry, attempt limit, one-time use) and who is allowed to see what.

## Project structure

```text
config/       settings and root URLs
store/        categories, products, photos, features, stock history
accounts/     signup, login, profile, addresses, OTP
orders/       cart, checkout, orders
dashboard/    owner panel (staff only)
templates/    HTML templates
static/       CSS and JavaScript
```

## Design decisions

- **Selling price is calculated.** The owner enters MRP and discount percentage. The price is saved when the product is saved, so it can be filtered and sorted in the database.
- **Orders keep their own copy** of the name, price, address and mobile number. Changing a product or an address never changes a past order.
- **One function changes stock.** Online orders, cancellations and the owner's changes all go through it, so every change is logged and stock cannot go below zero, even with simultaneous orders.
- **Placing an order is all or nothing.** If one item has just sold out, no order is created and no stock is lost.
- **Owner pages are protected on the server** and customers only ever see their own data.
- **Secrets live in `.env`**, which is not in Git.

## Notes

OTP runs in **demo mode**: the code is printed in the terminal and shown on screen, and no real SMS is sent. A real SMS provider can be added in one place (`accounts/otp.py`) without changing the rest of the code.

## Roadmap

- [x] Project setup, settings, base template
- [x] Product catalog and admin
- [x] Storefront: categories, search, filters, pagination
- [x] Accounts and saved addresses
- [x] Cart
- [x] Checkout and Cash on Delivery orders
- [x] Owner panel: orders, stock, products
- [x] Mobile OTP (demo mode)
- [x] Automated tests
- [ ] Styling polish
- [ ] Deployment (PostgreSQl, cloud image storage)
