def reconcile(current, desired):
    return [['set', key, value] for key, value in desired.items()]
