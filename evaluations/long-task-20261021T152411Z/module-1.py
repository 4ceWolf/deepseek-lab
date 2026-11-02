def apply_events(initial, events):
    result = dict(initial)

    for event in events:
        op = event.get("op")
        if op != "put":
            raise ValueError("Unknown operation")

        key = event["key"]
        value = event["value"]
        result[key] = value

    return result