def apply_events(initial, events):
    result = dict(initial)

    for event in events:
        op = event.get("op")

        if op == "put":
            key = event["key"]
            value = event["value"]
            result[key] = value
        elif op == "delete":
            key = event["key"]
            if key in result:
                del result[key]
        elif op == "add":
            key = event["key"]
            value = event["value"]
            result[key] = result.get(key, 0) + value
        else:
            raise ValueError("Unknown operation")

    return result