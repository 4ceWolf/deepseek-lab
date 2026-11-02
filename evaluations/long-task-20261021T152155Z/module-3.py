def apply_events(initial, events):
    result = dict(initial)
    for event in events:
        op = event.get("op")
        if op == "put":
            result[event["key"]] = event["value"]
        elif op == "delete":
            result.pop(event["key"], None)
        elif op == "add":
            key = event["key"]
            result[key] = result.get(key, 0) + event["value"]
        elif op == "rename":
            old = event["old"]
            new = event["new"]
            if old not in result:
                raise ValueError("rename source missing: %r" % (old,))
            if old != new and new in result:
                raise ValueError("rename target exists: %r" % (new,))
            if old != new:
                result[new] = result.pop(old)
        else:
            raise ValueError("unknown op: %r" % (op,))
    return result