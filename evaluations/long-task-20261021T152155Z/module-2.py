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
        else:
            raise ValueError("unknown op: %r" % (op,))
    return result