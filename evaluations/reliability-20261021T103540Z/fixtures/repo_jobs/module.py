def plan_jobs(jobs, now, limit):
    jobs.sort(key=lambda j: j['due'])
    return [j['id'] for j in jobs if j['due'] < now][:limit]
