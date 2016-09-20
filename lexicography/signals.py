import django.dispatch

entry_available = django.dispatch.Signal(providing_args=["instance"])
"""
Sent when an entry becomes available. This may be because a
*new* entry is created or because an old entry is undeleted.
"""

entry_unavailable = django.dispatch.Signal(providing_args=["instance"])
"""
Sent when an entry becomes unavailable. This is because an entry
was deleted.
"""

entry_newly_published = django.dispatch.Signal(providing_args=["instance"])
"""
Sent when an entry becomes published. Note that if a version of an
entry was already published and a new version is published, this
signal is not sent.
"""

entry_unpublished = django.dispatch.Signal(providing_args=["instance"])
"""
Sent when an entry becomes unpublished, which means that no
version of this entry is published.
"""

changerecord_hidden = django.dispatch.Signal(providing_args=["instance"])
"""
Sent when an changerecord becomes hidden. If a a changerecord is
created hidden, then this signal will be sent.
"""

changerecord_shown = django.dispatch.Signal(providing_args=["instance"])
"""
Sent when an changerecord was hidden but becomes shown (not
hidden). Note that we do not send this signal when a change record is
*created*.
"""
