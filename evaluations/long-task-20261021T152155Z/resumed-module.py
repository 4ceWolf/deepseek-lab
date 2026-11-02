def _run_event(result, event):
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
    elif op == "expect":
        key = event["key"]
        value = event["value"]
        if value is None:
            if key in result:
                raise ValueError("expect absent failed: %r" % (key,))
        else:
            if key not in result or result[key] != value:
                raise ValueError("expect mismatch: %r" % (key,))
    elif op == "batch":
        _run_events(result, event["events"])
    else:
        raise ValueError("unknown op: %r" % (op,))


def _run_events(result, events):
    for event in events:
        _run_event(result, event)


def apply_events(initial, events):
    result = dict(initial)
    _run_events(result, events)
    return result


def replay(initial, events):
    result = dict(initial)
    snapshots = []
    for event in events:
        _run_event(result, event)
        snapshots.append(dict(result))
    return snapshots


def diff_events(before, after):
    events = []
    for key in sorted(before):
        if key not in after:
            events.append({"op": "delete", "key": key})
    for key in sorted(after):
        if key not in before:
            events.append({"op": "put", "key": key, "value": after[key]})
        elif after[key] != before[key]:
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
        "total": total,
    }


def compact_events(initial, events):
    return diff_events(initial, apply_events(initial, events))