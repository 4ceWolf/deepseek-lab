def cumulative(events):
    totals = {}
    for name, delta in events:
        totals[name] = delta
    return totals
