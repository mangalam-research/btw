import django.dispatch

semantic_field_updated = django.dispatch.Signal(providing_args=["instance"])
"""
Sent when a semantic field has been updated.
"""
