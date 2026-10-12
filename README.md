# Radhe Krishna Store

An online store website for a single shop, built with Django. Customers can browse products by category, add items to a cart and place Cash on Delivery orders. The owner manages products, stock and orders from a separate panel.

> **Status:** work in progress. See the roadmap below.

## Features

**Customer**
- Browse products by category, with price range filter, sorting, search and pagination
- Product page with multiple photos and size selection for clothes
- Sign up and log in, with a saved address and mobile number
- Cart and Cash on Delivery checkout
- Order history with delivery contact details

**Owner**
- Separate panel for new orders and order status
- Manual stock updates (for offline and online sales), with a stock history log
- Product management with multiple photos

## Tech stack

- Python 3.13
- Django 5.2 (LTS)
- SQLite (development)
- HTML, CSS, JavaScript
- python-decouple for environment variables
- Pillow for image uploads

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

Then run:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`.

## Project structure

```
config/       project settings and root URLs
store/        categories, products, images, stock
accounts/     signup, login, profile, address, OTP
orders/       cart, checkout, orders
dashboard/    owner panel
templates/    HTML templates
static/       CSS, JavaScript, images
```

## Roadmap

- [x] Project setup, settings, base template
- [ ] Product catalog and admin
- [ ] Storefront pages (categories, search, filters)
- [ ] Accounts and saved address
- [ ] Cart
- [ ] Checkout and Cash on Delivery orders
- [ ] Owner dashboard (orders and stock)
- [ ] Mobile OTP verification (demo mode)
- [ ] Tests and deployment

## Note on OTP

Mobile OTP runs in **demo mode**: the code is printed in the terminal and shown on screen. No real SMS is sent. A real SMS provider can be plugged in without changing the rest of the code.