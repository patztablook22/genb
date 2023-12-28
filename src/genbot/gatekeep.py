import asyncio

def gatekeep(fn):
    running = {}
    async def wrapper(*args, **kwargs):
        async def wrapper_inner():
            params = tuple(args)
            force = kwargs.get('force', False)
            if not force and params in running: return
            running[params] = running.get(params, 0) + 1
            await fn(*args)
            running[params] -= 1
            if running[params] == 0: del running[params]

        await asyncio.create_task(wrapper_inner())

    return wrapper
