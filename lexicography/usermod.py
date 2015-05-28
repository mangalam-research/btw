from django.contrib.auth.models import Group

#
# Why this module? The functions here could be added as methods to a
# custom user model or we could use a proxy model, etc. A custom user
# model runs the risk of conflict with custom apps we might want to
# use in the future. ``request.user`` is not set to a proxy model so
# we'd have to do it ourselves or write an authentication backend
# which would have to be compatible with allauth. Lots of potential
# for problems.
#
# So here we are...


def can_author(user):
    scribe = Group.objects.get(name='scribe')
    for perm in scribe.permissions.all():
        if not user.has_perm("{0.content_type.app_label}.{0.codename}"
                             .format(perm)):
            return False
    return True
