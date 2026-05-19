#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def bootstrap_runserver():
    """Prepare a fresh checkout before the dev server starts."""
    from django.contrib.auth import get_user_model
    from django.core.management import call_command

    call_command('migrate', interactive=False, verbosity=0)

    User = get_user_model()
    if not User.objects.exists():
        call_command('seed_demo', verbosity=0)


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    if len(sys.argv) > 1 and sys.argv[1] == 'runserver' and os.environ.get('RUN_MAIN') == 'true':
        import django

        django.setup()
        bootstrap_runserver()

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
