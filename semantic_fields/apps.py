from django.apps import AppConfig
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

class DefaultAppConfig(AppConfig):
    name = 'semantic_fields'

    def ready(self):
        #
        # Yup, we patch the user model to add some methods for
        # checking permissions that are pertinent to this app. This is
        # the least problematic of a bunch of approaches:
        #
        # 1. Proxy: the problem is that Django won't return proxies
        # from querying the database. In particular ``request.user``
        # won't be a proxy unless we start mucking about elsewhere in
        # Django. Adding just one method would have a ripple effect.
        #
        # 2. Using a ``OneToOneField`` to introduce a related model
        # only so that we can have custom methods is completely
        # asinine. This means modifying the database for something
        # that has no existence in the database. It also means slowing
        # database requests on users.
        #
        # 3. Using a custom user model would work but there is
        # effectively a single slot for user customization. If we use
        # a tool in the future that requires its own model, we've
        # already taken the slot.
        #
        # Patching the class is in effect no more risky than adding a
        # method on a derived class. The added method could just as
        # well clash with methods on the base class.
        #

        user = get_user_model()

        @property
        def can_add_semantic_fields(self):
            return self.has_perm("semantic_fields.add_semanticfield")

        user.add_to_class("can_add_semantic_fields", can_add_semantic_fields)

        setattr(AnonymousUser, "can_add_semantic_fields",
                can_add_semantic_fields)

        @property
        def can_change_semantic_fields(self):
            return self.has_perm("semantic_fields.change_semanticfield")

        user.add_to_class(
            "can_change_semantic_fields", can_change_semantic_fields)

        setattr(AnonymousUser, "can_change_semantic_fields",
                can_change_semantic_fields)
