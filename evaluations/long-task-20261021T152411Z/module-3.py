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
        elif op == "rename":
            old = event["old"]
            new = event["new"]

            if old not in result:
                raise ValueError("Missing old key")

            if old == new:
                continue

            if new in result:
                raise ValueError("New key already exists")

            value = result[old]
            del result[old]
            result[new] = value
        else:
            raise ValueError("Unknown operation")

    return result