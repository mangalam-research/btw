"""
This module implements the functionality required for locking
lexicographical entries. An entry ``E`` can be in the following locking
states:

* Unlocked: there is no :class:`.EntryLock` for ``E``.

The possible state transitions are:

* Unlocked -> Locked: when ``E`` is locked.

* Locked -> Locked: when ``E``'s lock is refreshed.

* Locked -> Unlocked
"""


from django.template.response import TemplateResponse
from django.http import HttpResponse
from django.conf import settings
from django.db import transaction

import json
import logging
import lib.util as util
from functools import wraps

from .models import Entry, EntryLock

logger = logging.getLogger(__name__)


def _report(lock, action, user=None, lock_id=None):
    if user is None:
        user = lock.owner
    if lock_id is None:
        lock_id = lock.id
    logger.debug((u"{2} {1} lock {3} on entry {0.entry.id} "
                  "(headword: {0.entry.headword})").format(lock, action, user,
                                                           lock_id))


def _acquire_entry_lock(entry, user):
    """
Acquire the lock. The caller must make sure that there is no lock yet
on the entry before calling this function.

:param entry: The entry for which to acquire the lock.
:type entry: :class:`.Entry`
:param user: The user who is acquiring the lock.
:type user: The value of :attr:`settings.AUTH_USER_MODEL` determines the class.
:returns: The lock if the lock was acquired, or ``None`` if not.
:rtype: :class:`.EntryLock`
"""
    lock = EntryLock()
    lock.entry = entry
    now = util.utcnow()
    lock.owner = user
    lock.datetime = now
    lock.save()

    _report(lock, "acquired")
    return lock


@transaction.atomic
def release_entry_lock(entry, user):
    """
Release the lock on an entry. It is a fatal error to call this
function with a user who does not currently own the lock on the entry
passed to the function.

:param entry: The entry for which we want to release the lock.
:type entry: :class:`.Entry`
:param user: The user requesting the release.
:type user: The value of :attr:`settings.AUTH_USER_MODEL` determines the class.
"""
    lock = EntryLock.objects.select_for_update().get(entry=entry)
    if lock.owner != user:
        raise ValueError("the user releasing the lock is not the one who owns "
                         "it")

    lock_id = lock.id
    lock.delete()
    _report(lock, "released", lock_id=lock_id)


def _refresh_entry_lock(lock):
    """
Refresh the entry lock.

:param lock: The lock to update.
:type lock: :class:`.EntryLock`
"""
    lock.datetime = util.utcnow()
    lock.save()
    _report(lock, "refreshed")


def _expire_entry_lock(lock, user):
    """
Expire the entry lock.

:param lock: The lock to update.
:type lock: :class:`.EntryLock`
:param user: The user updating the lock.
:type user: The value of :attr:`settings.AUTH_USER_MODEL` determines the class.
"""
    if lock.expirable:
        lock_id = lock.id
        lock.delete()
        _report(lock, "expired", user, lock_id)
        return True
    _report(lock, "failed to expire", user)
    return False


@transaction.atomic
def try_acquiring_lock(entry, user):
    """
Attempt to acquire the lock.

:param lock: The lock to update.
:type lock: :class:`.EntryLock`
:param user: The user updating the lock.
:type user: The value of :attr:`settings.AUTH_USER_MODEL` determines the class.
:returns: The lock if successful. ``None`` otherwise.
:rtype: :class:`.EntryLock`
"""
    lock = None
    try:
        lock = entry.entrylock_set.all().select_for_update()[0]
    except IndexError:
        pass

    if lock is None:
        # There's no current lock for this entry.
        lock = _acquire_entry_lock(entry, user)
    elif lock.owner == user:
        # We already own the lock.
        _refresh_entry_lock(lock)
    else:
        # Try to expire the other user's lock.
        if _expire_entry_lock(lock, user):
            # It expired!
            lock = _acquire_entry_lock(entry, user)
        else:
            # It was not expirable...
            lock = None

    return lock


def entry_lock_required(view):
    """
Decorator that acquires the lock before the view is called. The
decorator expects that the view will be called with a keyword argument
named ``entry_id`` which is the key of the entry for which the lock
must be acquired.

For on-Ajax requests, if the locking fails the user is show a page
with an error message. For Ajax requests, an Ajax response is sent
back.

:param view: The view to decorate.
:returns: The wrapped view.
"""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        entry_id = kwargs['entry_id']
        entry = Entry.objects.get(id=entry_id)
        user = request.user
        lock = try_acquiring_lock(entry, user)
        if lock is None:
            # Ok, we just did not manage to get the lock, tell the user.
            lock = EntryLock.objects.get(entry=entry_id)
            if request.is_ajax():
                messages = [
                    {'type': 'locked',
                     'msg': 'The entry is locked by user %s' % str(lock.owner)}
                ]
                resp = json.dumps({'messages': messages}, ensure_ascii=False)
                return HttpResponse(resp, content_type="application/json")
            else:
                return TemplateResponse(
                    request, 'lexicography/locked.html',
                    {'page_title': settings.BTW_SITE_NAME + " | Lexicography",
                     'lock': lock})
        return view(request, *args, **kwargs)
    return wrapper
