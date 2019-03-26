from .util import utcnow

TIMEOUT = 60

class Falsy(object):

    def __bool__(self):
        return False

HELD = Falsy()
SET = Falsy()

def acquire_mutex(cache, key, task_id, logger):
    """
    Attempt acquiring a mutex from the cache. This relies on the cache
    backend supporting setting keys atomically. Only Redis is
    supported for now. If the mutex is acquired, the key will get a
    value of ``{ "task": task_id}`` where ``task_id`` is the parameter
    passed to this function. This function records failure to acquire
    the mutex on the logger.

    :param cache: The cache in which the mutex lives. This must be a
                  Redis cache.
    :param key: The key which serves as mutex.
    :type key: :class:`str`
    :param task_id: The identifier of the task trying to acquire the mutex.
    :type task_id: :class:`str`
    :param logger: The logger on which to record failure.
    """
    if task_id is None:
        raise ValueError(
            "task_id cannot be None; if your task is synchronous "
            "please create a unique fake id")

    # We attempt to claim this key for ourselves. nx=True is a feature
    # of the Redis backend. The key will be atomically set if not yet
    # set. A return value of True means it was set.
    value = {"task": task_id, "datetime": utcnow()}
    ours = cache.set(key, value, nx=True, timeout=TIMEOUT)
    if ours:
        return value

    prev = cache.get(key)
    other = isinstance(prev, dict) and prev.get("task")

    # We still own the mutex
    if other is not None and other == task_id:
        return prev

    if other:
        logger.debug("%s is held by %s; ending task.",
                     key, other)
        return HELD

    logger.debug("%s is set; ending task.", key)
    return SET
