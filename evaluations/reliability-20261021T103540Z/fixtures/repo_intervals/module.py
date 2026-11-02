def merge_windows(windows):
    windows.sort()
    out = []
    for start, end in windows:
        if out and start < out[-1][1]:
            out[-1][1] = end
        else:
            out.append([start, end])
    return out
