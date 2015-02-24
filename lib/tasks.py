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

    # We attempt to claim this key for ourselves. nx=True is a feature
    # of the Redis backend. The key will be atomically set if not yet
    # set. A return value of True means it was set.
    ours = cache.set(key, {"task": task_id}, nx=True)
    if ours:
        return True

    prev = cache.get(key)
    other = prev.get("task")
    if other:
        logger.debug("%s is held by %s; ending task.",
                     key, other)
    else:
        logger.debug("%s is set; ending task.", key)

    return False
