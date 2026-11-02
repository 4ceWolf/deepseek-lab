def merge_config(layers):
    out = layers[0] if layers else {}
    for layer in layers[1:]:
        for key, value in layer.items():
            if value:
                out[key] = value
    return out
