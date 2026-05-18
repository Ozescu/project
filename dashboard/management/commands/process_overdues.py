from django.core.management.base import BaseCommand

from loans.services import refresh_overdue_loans


class Command(BaseCommand):
    help = 'Process overdue loans, reminders, notifications and sanctions.'

    def handle(self, *args, **options):
        refresh_overdue_loans()
        self.stdout.write(self.style.SUCCESS('Processed overdues'))
