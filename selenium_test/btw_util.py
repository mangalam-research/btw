
require_sense_recording = {}


def record_senses(f):
    """
    This is a decorator used to mark a step as requiring that senses be
    recorded. This decorator must come **before** the decorators used
    by behave.
    """
    require_sense_recording[f] = True
    return f
