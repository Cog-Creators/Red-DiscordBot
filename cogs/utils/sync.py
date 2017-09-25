import io

try:
    import requests
except ImportError:
    print("Requests module not installed, sync functions unavailable!")

class ResponseError(BaseException):
    pass

class Route:
    def __init__(self, base_url, path, cdn_url=None, method="GET", headers=None):
        self.base_url = base_url
        self.path = path
        self.method = method
        self.headers = headers
        self.cdn_url = cdn_url

    def sync_query(self, url_params=None):
        res = getattr(requests, self.method.lower())(
                self.base_url+self.path, headers=self.headers)
        if 200 <= res.status_code < 300:
            retval = res.json()

            # Some endpoints are not images
            if self.cdn_url is None:
                return retval
            return Result(**retval, cdn_url=self.cdn_url)

        else:
            raise ResponseError(
                    "Expected a status code 200-299, got {} \n{}"
                    .format(res.status_code, self.base_url+self.path))

    def __call__(self, url_params=None):
        return self.sync_query(url_params)

class Result:
    def __init__(self, path, id, type, nsfw, cdn_url):
        self.path = path
        self.cdn_path = path[2:]
        self.img_id = id
        self.img_type = type
        self.nsfw = nsfw
        self.cdn_url = cdn_url

    def sync_download(self):
        res = requests.get(self.cdn_url+self.cdn_path)
        if 200 <= res.status_code < 300:
            return io.BytesIO(res.content)
        else:
            raise ResponseError(
                    "Expected a status code 200-299, got {}"
                    .format(res.status_code))

    def __call__(self):
        return self.sync_download()
