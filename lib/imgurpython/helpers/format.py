from ..helpers import Comment
from ..helpers import GalleryAlbum
from ..helpers import GalleryImage
from ..helpers import Notification


def build_comment_tree(children):
    children_objects = []
    for child in children:
        to_insert = Comment(child)
        to_insert.children = build_comment_tree(to_insert.children)
        children_objects.append(to_insert)

    return children_objects


def format_comment_tree(response):
    if isinstance(response, list):
        result = []
        for comment in response:
            formatted = Comment(comment)
            formatted.children = build_comment_tree(comment['children'])
            result.append(formatted)
    else:
        result = Comment(response)
        result.children = build_comment_tree(response['children'])

    return result


def build_gallery_images_and_albums(response):
        if isinstance(response, list):
            result = []
            for item in response:
                if item['is_album']:
                    result.append(GalleryAlbum(item))
                else:
                    result.append(GalleryImage(item))
        else:
            if response['is_album']:
                result = GalleryAlbum(response)
            else:
                result = GalleryImage(response)

        return result


def build_notifications(response):
    result = {
        'replies': [],
        'messages': [Notification(
            item['id'],
            item['account_id'],
            item['viewed'],
            item['content']
        ) for item in response['messages']]
    }

    for item in response['replies']:
        notification = Notification(
            item['id'],
            item['account_id'],
            item['viewed'],
            item['content']
        )
        notification.content = format_comment_tree(item['content'])
        result['replies'].append(notification)

    return result


def build_notification(item):
    notification = Notification(
        item['id'],
        item['account_id'],
        item['viewed'],
        item['content']
    )

    if 'comment' in notification.content:
        notification.content = format_comment_tree(item['content'])

    return notification
