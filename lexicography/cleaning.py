import datetime
import itertools

from django.conf import settings
from django.db.models import Count
from django.db import transaction

from .models import ChangeRecord, Chunk
from lib.cleaning import Cleaner

class ChangeRecordCleaner(Cleaner):

    @property
    def total_count(self):
        return ChangeRecord.objects.all().count()

    def check_unpublished(self, obj, verbose=True):
        "Check that a record is not published."
        ret = not obj.published
        if not ret and self.verbose and verbose:
            self.emit_keep(obj, "it is published")
        return ret

    def check_old_enough(self, obj, verbose=True):
        "Check that a record is old enough to be cleaned."
        ret = self.now - obj.datetime >= \
            datetime.timedelta(days=self.age_limit)
        if not ret and self.verbose and verbose:
            self.emit_keep(obj, "it is not old enough")
        return ret

    def execute_clean(self, obj):
        obj.hidden = True
        obj.save()

class ChangeRecordCollapser(ChangeRecordCleaner):
    """
    "Collapse" :class:`.ChangeRecord` objects. The collapsing
    operation aims to reduce the number of visible ``ChangeRecord``
    objects by reducing the number of records that point to the same
    version of an :class:`.Entry` (to the same
    :class:`.Chunk`). Objects that are "collapsed" are marked as
    "hidden".

    For all :class:`.Entry` records that have a version that is
    referenced by more than one :class:`.ChangeRecord`, one of the
    ``ChangeRecord`` records will be elected "to keep". We prefer to
    keep a published record because these are not subject to deletion,
    but if no such record exists, then some other record will be
    elected "to keep". All other ``ChangeRecord`` objects that point
    to the same version are cleaned.

    In any case we do not clean published records, or records that
    are too young. A record is too young if its age is equal or less
    than the setting named ``BTW_COLLAPSE_CRS_OLDER_THAN``.
    """

    def __init__(self, *args, **kwargs):
        super(ChangeRecordCollapser, self).__init__(*args, **kwargs)
        self.age_limit = settings.BTW_COLLAPSE_CRS_OLDER_THAN
        self._to_keep = set()

    def check_can_be_cleaned(self, obj, verbose=True):
        """Check that a record is not "to keep"."""
        ret = obj.id not in self._to_keep
        if not ret and self.verbose and verbose:
            self.emit_keep(
                obj, "we need to keep one change record for a given hash")
        return ret

    def check_right_type(self, obj, verbose=True):
        """
        Check that a the record is of the right type. It must not be a
        CREATE record.
        """
        ret = obj.ctype != ChangeRecord.CREATE
        if not ret and self.verbose and verbose:
            self.emit_keep(obj, "it is the wrong type")
        return ret

    @property
    def to_clean(self):
        active = ChangeRecord.objects.active()

        # This will contain entries for which there is more than one
        # ChangeRecord with the same c_hash.
        entry_hash = active.values('entry', 'c_hash') \
            .annotate(count=Count('c_hash')).filter(count__gt=1) \
            .distinct()

        to_clean = set()
        for entry, c_hash in [(r["entry"], r["c_hash"]) for r in entry_hash]:
            candidates = active.select_for_update().filter(entry=entry,
                                                           c_hash=c_hash) \
                .order_by('-datetime')

            candidates_to_clean = set()
            candidates_to_keep = set()
            for candidate in candidates:
                if self.perform_checks(candidate, True):
                    candidates_to_clean.add(candidate)
                else:
                    candidates_to_keep.add(candidate)

            #
            # For each set of candidates we must keep at least one record.
            # If nothing is going to be kept, then we select an arbitrary
            # record, which here is the most recent one.
            #
            # This should be a very unusual situation. All articles
            # start with a CREATE record. And at the time of writing,
            # there is no other mechanism that hides or deletes CREATE
            # records. Therefore all articles should have at least one
            # record already deemed "to keep": the CREATE record. So
            # there should be no need to elect an arbitrary
            # record. There's no telling however if in the future the
            # rules may change. So we have this provision.
            #
            if len(candidates_to_keep) == 0:
                keep = candidates[0]
                candidates_to_clean.remove(keep)
                candidates_to_keep.add(keep)
                self._to_keep.add(keep.id)
                # We artificially call the check here so that a reason is
                # emitted.
                self.check_can_be_cleaned(keep)

            to_clean.update(candidates_to_clean)
        return to_clean

class OldVersionCleaner(ChangeRecordCleaner):
    """
    Clean old versions of :class:`.Entry` records. Contrarily to
    :class:`.ChangeRecordCollapser`, this cleaner does cause
    :class:`.Chunk` objects to become hidden to the system.

    This cleans :class:`.ChangeRecord` objects that:

    * Are not published, and

    * Are not the latest version of an ``Entry``, and

    * Are old enough, and

    * Are either of type :attr:`.ChangeRecord.RECOVERY` or of type
      :attr:`.ChangeRecord.UPDATE` and subtype
      :attr:`.ChangeRecord.AUTOMATIC`.

    A record is "old enough" if its age is greater than the
    setting named ``BTW_COLLAPSE_CRS_OLDER_THAN``.
    """

    def __init__(self, *args, **kwargs):
        super(OldVersionCleaner, self).__init__(*args, **kwargs)
        self.age_limit = settings.BTW_CLEAN_CRS_OLDER_THAN

    def check_not_latest(self, obj, verbose=True):
        """
        Check that a the record is not the latest version of an
        :class:`.Entry`.
        """
        ret = obj.entry.latest.id != obj.id
        if not ret and self.verbose and verbose:
            self.emit_keep(obj, "it is the latest version of its article")
        return ret

    def check_right_type(self, obj, verbose=True):
        """
        Check that a the record is of the right type. It must be either a
        recovery record or an automatic update.
        """
        ret = obj.csubtype == ChangeRecord.RECOVERY or \
            (obj.csubtype == ChangeRecord.AUTOMATIC and
             obj.ctype == ChangeRecord.UPDATE)
        if not ret and self.verbose and verbose:
            self.emit_keep(obj, "it is the wrong type")
        return ret

    @property
    def to_clean(self):
        return set(cr for cr in ChangeRecord.objects.active()
                   .select_for_update() if self.perform_checks(cr, True))
