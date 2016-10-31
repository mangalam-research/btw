from importlib import import_module

from django.core.management.base import BaseCommand, CommandError
from django.contrib.sessions.backends import db as db, cached_db as cached_db
from django.conf import settings
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = """\
Logs all users out of the server.
"""

    def add_arguments(self, parser):
        parser.add_argument('--noop',
                            action='store_true',
                            dest='noop',
                            default=False,
                            help='Do everything except performing the change.')

    def handle(self, *args, **options):
        engine = import_module(settings.SESSION_ENGINE)
        User = get_user_model()

        #
        # For now we only support database engines for sessions.
        #
        # See:
        #
        #
        #
        # * http://stackoverflow.com/questions/953879/how-to-force-user-logout-in-django   # nopep8
        #
        # * https://django-force-logout.readthedocs.org/en/latest/,
        #   which is an implementation of Clement's answer over at
        #   stackoverflow.
        #
        # Since we want to log out everybody, some of the issues
        # raised in the SO Q&A do not apply here.
        #
        if not (engine == db or engine == cached_db):
            raise CommandError(
                "This command works only with sessions that are backed "
                "by a database.")

        # Get rid of expired sessions immediately.
        engine.SessionStore.clear_expired()
        store = engine.SessionStore()

        for session in Session.objects.all():
            uid = session.get_decoded().get('_auth_user_id', None)
            user = None

            try:
                user = User.objects.get(pk=uid) if uid is not None else None
            except User.DoesNotExist:
                pass

            name = user.username if user is not None else None

            if name is not None:
                print "Logging out user {0} from session {1}." \
                    .format(name, session.session_key)
            else:
                print "Deleting session.", session.session_key

            if not options['noop']:
                store.delete(session.session_key)
