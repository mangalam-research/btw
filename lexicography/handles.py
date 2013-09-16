"""Library for managing handles.

.. moduleauthor:: Louis-Dominique Dubeau <ldd@lddubeau.com>

"""
from django.db.models import Max
from django.db import transaction

from .models import Handle

class HandleManager(object):
    """
    This class manages the mapping between entry ids and handles used
    for saving data. The handles provided by this class are passed to
    the editor instance embedded in pages that edit lexicographic
    entries. These handles are then used when saving the data back
    onto the server to refer to specific entries.

    The main advantage of using system is that it is possible to have
    unassociated handles representing new articles that have not yet
    been saved. The alternative would be to create a fake article
    whenever a user asks to create a new article. If the user then
    aborted the edition by reloading, or turning off the browser or
    some similar non-explicit action, these preemptively created
    articles would then be left over on the system. Entry validation
    would also be problematic because the Entry objects for these
    prospective articles would have a headword which is NULL or would
    have a placeholder headword which would be duplicated or some
    nonsense string. Or we'd have to ask the user for a headword ahead
    of time. None of these solutions are pain-free.

    The handle->id mapping allows the system to give a handle that is not
    associated **yet** with an article. Upon first save the server can
    then associate an id with it.

    One object of this class must be created per session. The handles
    provided by this class are guaranteed to be unique within a session.

    :param session_key: The session key of the session associated with
                        this object.
    :type session_key: str

    .. warning:: This class is not designed to provide security.
    """
    def __init__(self, session_key):
        self.session_key = session_key
        self.handle_to_handle_obj_id = {}
        self.handle_to_entry_id = {}
        self.entry_id_to_handle = {}

    def make_unassociated(self):
        """
        Create an unassociated handle.

        :returns: The handle. Guaranteed to be unique for this session.
        :rtype: str
        """
        if not transaction.is_managed():
            raise Exception("transactions must be managed")

        max_handle = Handle.objects.select_for_update(). \
                     filter(session=self.session_key). \
                     aggregate(Max('handle'))['handle__max']

        handle = 0 if max_handle is None else max_handle + 1
        handle_obj = Handle(handle=handle, session=self.session_key)
        handle_obj.save()

        self.handle_to_handle_obj_id[handle] = handle_obj.id
        self.handle_to_entry_id[handle] = None
        return handle

    def associate(self, handle, entry_id):
        """
        Associate an unassociated handle with an id. It is illegal to
        associate a handle with more than one entry. It is also
        illegal to have two handles point to the same entry.

        :param handle: The handle.
        :type handle: str
        :param entry_id: The entry id.
        :type entry_id: int
        """
        if not transaction.is_managed():
            raise Exception("transactions must be managed")

        if self.id(handle) is not None:
            raise ValueError("handle {0} already associated".format(handle))

        if self.entry_id_to_handle.get(entry_id, None) is not None:
            raise ValueError("id {0} already associated".format(entry_id))

        handle_obj = Handle.objects.select_for_update().get(
            id=self.handle_to_handle_obj_id[handle])
        handle_obj.entry_id = entry_id
        handle_obj.save()

        self.handle_to_entry_id[handle] = entry_id
        self.entry_id_to_handle[entry_id] = handle

    def id(self, handle):
        """
Return the id associated with a handle.

:param handle: The handle.
:type handle: str
:returns: The id.
:rtype: int or None
"""
        if not transaction.is_managed():
            raise Exception("transactions must be managed")

        # If it is there and not none, it can't have changed, so we
        # don't have to read the database.
        if handle in self.handle_to_entry_id and \
           self.handle_to_entry_id[handle] is not None:
            return self.handle_to_entry_id[handle]

        # Otherwise, check whether it has been associated.
        try:
            handle_obj = Handle.objects.get(session=self.session_key,
                                            handle=handle)
        except Handle.DoesNotExist:
            raise ValueError("handle {0} does not exist".format(handle))

        entry_id = handle_obj.entry.id if handle_obj.entry is not None else None
        self.handle_to_entry_id[handle] = entry_id
        self.handle_to_handle_obj_id[handle] = handle_obj.id
        if entry_id is not None:
            self.entry_id_to_handle[entry_id] = handle
        return entry_id

_hms = {}

def get_handle_manager(session):
    """
If the session already has a HandleManager, return it. Otherwise,
create one, associate it with the session and return it.

:param session: The session.
:type session: :py:class:`django.contrib.sessions.backends.base.SessionBase`
:returns: The handle manager.
:rtype: :py:class:`HandleManager`
"""
    hm = _hms.get(session.session_key, None)
    if hm is None:
        hm = HandleManager(session.session_key)
        _hms[session.session_key] = hm

    return hm
