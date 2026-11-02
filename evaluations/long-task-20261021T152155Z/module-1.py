def apply_events(initial, events):
    result = dict(initial)
    for event in events:
        op = event.get("op")
        if op == "put":
            result[event["key"]] = event["value"]
        else:
            raise ValueError("unknown op: %r" % (op,))
    return result