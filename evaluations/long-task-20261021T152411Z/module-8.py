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
    elif op == "expect":
        key = event["key"]
        value = event["value"]

        if value is None:
            if key in result:
                raise ValueError("Expectation failed")
        else:
            if key not in result or result[key] != value:
                raise ValueError("Expectation failed")
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

def diff_events(before, after):
    events = []

    removed = []
    for key in before:
        if key not in after:
            removed.append(key)
    removed.sort()
    for key in removed:
        events.append({"op": "delete", "key": key})

    changed = []
    for key in after:
        if key not in before or before[key] != after[key]:
            changed.append(key)
    changed.sort()
    for key in changed:
        events.append({"op": "put", "key": key, "value": after[key]})

    return events

def audit(initial, events):
    final = apply_events(initial, events)
    history = replay(initial, events)
    changes = diff_events(initial, final)
    total = sum(final.values())
    return {
        "final": final,
        "history": history,
        "changes": changes,
        "total": total
    }