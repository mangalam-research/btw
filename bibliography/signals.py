import django.dispatch

#
# Contrarily to the signals in the lexicography app we do not care
# about items being added or removed. Added items are not an issue
# since articles are now allowed to refer to items before they
# exist. Removed items are not an issue because we do not allow
# deletion. (Except in rare, and very controled, instances.)
#

item_updated = django.dispatch.Signal(providing_args=["instance"])
"""
Sent when an item has been updated in a way that requires articles
that refer to it to be displayed differently.

This would mean a change in the title, date, or creators since these
are the only fields we use to render a secondary source in an article.

:param instance: The instance that was updated.
:type instance: :class:`bibliography.models.Item`
"""

primary_source_updated = django.dispatch.Signal(providing_args=["instances"])
"""
Sent when a primary source has been updated in a way that requires
articles that refer to it to be displayed differently.

This would mean a change in the reference title of the primary source,
since this is the only field we use for rendering such sources. A
change to the secondary source (the Item object) that is considered
significant also triggers this signal.

:param instances: The instances that were updated.
:type instances: :class:`list` of :class:`bibliography.models.PrimarySource`
"""
