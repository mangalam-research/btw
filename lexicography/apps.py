from django.apps import AppConfig
from django.contrib.auth import get_user_model

class DefaultAppConfig(AppConfig):
    name = 'lexicography'

    def ready(self):
        from . import usermod
        user = get_user_model()

        @property
        def can_author(self):
            return usermod.can_author(self)

        user.add_to_class("can_author", can_author)

        from django.contrib.auth.models import AnonymousUser
        setattr(AnonymousUser, "can_author", can_author)
