"""Library for managing handles.

.. moduleauthor:: Louis-Dominique Dubeau <ldd@lddubeau.com>

"""
import itertools

class HandleManager(object):
    """This class manages the mapping between entry ids and handles
used for saving data. The handles provided by this class are passed to
the editor instance embedded in pages that edit lexicographic
entries. These handles are then used when saving the data back onto
the server to refer to specific entries.

The main advantage of using system is that it is possible to have
unassociated handles representing new articles that have not yet been
saved. The alternative would be to create a fake article whenever a
user asks to create a new article. If the user then aborted the
edition by reloading, or turning off the browser or some similar
non-excplicit action, these preemptively created articles would then
be left over on the system. The handle->id mapping allows the system
to give a handle that is not associated **yet** with an article. Upon
first save the server can then associate an id with it.

One object of this class must be created per session. The handles
provided by this class are guaranteed to be unique within a session.

:param session_key: The session key of the session associated with this object.
:type session_key: str

.. warning:: This class is not designed to provide security.
"""
    def __init__(self, session_key):
        self.session_key = session_key
        self.handle_to_entry_id = {}
        self.entry_id_to_handle = {}
        self.__count = itertools.count()

    @property
    def _next_name(self):
        return self.session_key + "." + str(self.__count.next())

    def make_associated(self, entry_id):
        """
Create a new handle if there is no handle associated with the id. Otherwise, return the handle already associated with it.

:param entry_id: The id to associate.
:type entry_id: int
:returns: The handle.
:rtype: str
"""
        handle = self.entry_id_to_handle.get(entry_id, None)
        if handle is not None:
            return handle

        handle = self._next_name
        while handle in self.handle_to_entry_id:
            handle = self._next_name

        self.entry_id_to_handle[entry_id] = handle
        self.handle_to_entry_id[handle] = entry_id
        return handle

    def make_unassociated(self):
        """
Create an unassociated handle.

:returns: The handle.
:rtype: str
"""
        handle = self._next_name
        while handle in self.handle_to_entry_id:
            handle = self._next_name

        self.handle_to_entry_id[handle] = None
        return handle

    def associate(self, handle, entry_id):
        """
Associate an unassociated handle with an id.

:param handle: The handle.
:type handle: str
:param entry_id: The id.
:type entry_id: int
"""
        if self.handle_to_entry_id[handle] is not None:
            raise ValueError("handle {0} already associated".format(handle))

        if self.entry_id_to_handle.get(entry_id, None) is not None:
            raise ValueError("id {0} already associated".format(entry_id))

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
        return self.handle_to_entry_id[handle]

hms = {}
def get_handle_manager(session):
    """
If the session already has a HandleManager, return it. Otherwise,
create one, associate it with the session and return it.

:param session: The session.
:type session: :py:class:`django.contrib.sessions.backends.base.SessionBase`
:returns: The handle manager.
:rtype: :py:class:`HandleManager`
"""
    hm = hms.get(session.session_key, None)
    if hm is None:
        hm = HandleManager(session.session_key)
        hms[session.session_key] = hm
    return hm
