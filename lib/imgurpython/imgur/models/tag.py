from .gallery_album import GalleryAlbum
from .gallery_image import GalleryImage


class Tag(object):

    def __init__(self, name, followers, total_items, following, items):
        self.name = name
        self.followers = followers
        self.total_items = total_items
        self.following = following
        self.items = [GalleryAlbum(item) if item['is_album'] else GalleryImage(item) for item in items] \
            if items else None
