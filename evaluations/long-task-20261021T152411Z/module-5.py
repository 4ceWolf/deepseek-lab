def apply_events(initial, events):
    result = dict(initial)
    _process_events(result, events)
    return result

def _process_events(result, events):
    for event in events:
        _process_event(result, event)

def _process_event(result, event):
    op = event.get("op")

    if op == "put":
        result[event["key"]] = event["value"]
    elif op == "delete":
        key = event["key"]
        if key in result:
            del result[key]
    elif op == "add":
        key = event["key"]
        result[key] = result.get(key, 0) + event["value"]
    elif op == "rename":
        old = event["old"]
        new = event["new"]

        if old not in result:
            raise ValueError("Missing old key")

        if old == new:
            return

        if new in result:
            raise ValueError("New key already exists")

        value = result[old]
        del result[old]
        result[new] = value
    elif op == "batch":
        _process_events(result, event["events"])
    else:
        raise ValueError("Unknown operation")

def replay(initial, events):
    result = dict(initial)
    snapshots = []

    for event in events:
        _process_event(result, event)
        snapshots.append(dict(result))

    return snapshots