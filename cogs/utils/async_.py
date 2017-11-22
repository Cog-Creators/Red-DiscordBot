import io

try:
    import aiohttp
except ImportError:
    print("Aiohttp module not installed, async functions not available!")

from . import sync_


class Route(sync_.Route):
    async def async_query(self, url_params=None):
        async with aiohttp.ClientSession() as ses:
            async with getattr(ses, self.method.lower())(
                    self.base_url+self.path, headers=self.headers) as res:
                if 200 <= res.status < 300:
                    retval = await res.json()
                    if self.cdn_url is None:
                        return retval
                    return Result(**retval, cdn_url=self.cdn_url)

                else:
                    raise sync_.ResponseError(
                            "Expected a response code in range 200-299, got {}"
                            .format(res.status))


class Result(sync_.Result):
    async def async_download(self):
        async with aiohttp.ClientSession() as ses:
            async with ses.get(self.cdn_url+self.cdn_path) as res:
                if 200 <= res.status < 300:
                    return io.BytesIO(await res.read())
                else:
                    raise sync_.ResponseError(
                            "Expected a response code in range 200-299, got {}"
                            .format(res.status))
