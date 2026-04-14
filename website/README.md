# IntZam Website

This `website` folder is now a self-contained shareable website package.

It includes:
- a standalone Django backend
- Django admin for content editing
- website pages and assets
- public calculator APIs
- lead capture
- page, section, and content block editor models

## Structure

- `manage.py` - Django entry point
- `requirements.txt` - Python dependencies
- `web_project/` - Django project config
- `cms/` - standalone website CMS app
- `index.html`, `about.html`, `eligibility.html`, `civil-servants.html`, `calculator.html`, `contact.html`
- `styles.css`, `script.js`

## Quick Start

```bash
cd website
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_website
python manage.py createsuperuser
python manage.py runserver
```

Then open:

- `http://localhost:8000/` - public website
- `http://localhost:8000/admin/` - Django admin

## One-Click Windows Scripts

- `run_website.bat` - creates a virtualenv if needed, installs requirements, migrates, seeds, and starts the server
- `create_admin.bat` - creates a Django admin user

## What You Can Edit in Admin

- Website settings
- Public loan products for the calculator
- Website pages
- Website page sections
- Website page blocks
- Audiences
- FAQs
- Testimonials
- Website leads

## Image Editing Guide

- Homepage hero image: edit the `Home` record in `Website Pages`
- About page side illustration: edit the `About` record in `Website Pages`
- Eligibility page side illustration: edit the `Eligibility` record in `Website Pages`
- Civil servants page side illustration: edit the `Civil Servants` record in `Website Pages`
- Calculator page side illustration: edit the `Calculator` record in `Website Pages`
- Contact page side illustration: edit the `Contact` record in `Website Pages`

Each page now supports:
- `Hero image`
- `Illustration image`
- in-admin preview thumbnails for both

Sections and blocks also support:
- image preview thumbnails in admin
- ordering guidance using the `order` field
- recommended spacing like `10, 20, 30` for easier future inserts
- live preview links from page, section, and block editors to the public page

## Notes

- The website is now independent from the main LMS backend.
- Client portal links are configurable in `Website settings`.
- Hero images and block images are uploaded to `media/`.
- Branded placeholder assets live in `static/site/`.
- The Django admin homepage is customized for content editors with quick links and workflow guidance.
