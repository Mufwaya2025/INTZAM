from django.core.management.base import BaseCommand

from cms.models import bootstrap_website_content


class Command(BaseCommand):
    help = 'Seed standalone website content, products, pages, and editor blocks.'

    def handle(self, *args, **options):
        bootstrap_website_content()
        self.stdout.write(self.style.SUCCESS('Standalone website content seeded successfully.'))
