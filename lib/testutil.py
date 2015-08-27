def unmonkeypatch_databases():
    # Undo the monkeypatching we did in __init__ to detect
    # database accesses happening before we actually set our
    # environment to run the tests.
    from django.db import connections
    for name in connections:
        conn = connections[name]
        conn.connect = conn._old_connect
