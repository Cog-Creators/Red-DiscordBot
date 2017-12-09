import base64
import requests
from .imgur.models.tag import Tag
from .imgur.models.album import Album
from .imgur.models.image import Image
from .imgur.models.account import Account
from .imgur.models.comment import Comment
from .imgur.models.tag_vote import TagVote
from .helpers.error import ImgurClientError
from .helpers.format import build_notification
from .helpers.format import format_comment_tree
from .helpers.format import build_notifications
from .imgur.models.conversation import Conversation
from .helpers.error import ImgurClientRateLimitError
from .helpers.format import build_gallery_images_and_albums
from .imgur.models.custom_gallery import CustomGallery
from .imgur.models.account_settings import AccountSettings

API_URL = 'https://api.imgur.com/'
MASHAPE_URL = 'https://imgur-apiv3.p.mashape.com/'


class AuthWrapper(object):
    def __init__(self, access_token, refresh_token, client_id, client_secret):
        self.current_access_token = access_token

        if refresh_token is None:
            raise TypeError('A refresh token must be provided')

        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret

    def get_refresh_token(self):
        return self.refresh_token

    def get_current_access_token(self):
        return self.current_access_token

    def refresh(self):
        data = {
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token'
        }

        url = API_URL + 'oauth2/token'

        response = requests.post(url, data=data)

        if response.status_code != 200:
            raise ImgurClientError('Error refreshing access token!', response.status_code)

        response_data = response.json()
        self.current_access_token = response_data['access_token']


class ImgurClient(object):
    allowed_album_fields = {
        'ids', 'title', 'description', 'privacy', 'layout', 'cover'
    }

    allowed_advanced_search_fields = {
        'q_all', 'q_any', 'q_exactly', 'q_not', 'q_type', 'q_size_px'
    }

    allowed_account_fields = {
        'bio', 'public_images', 'messaging_enabled', 'album_privacy', 'accepted_gallery_terms', 'username'
    }

    allowed_image_fields = {
        'album', 'name', 'title', 'description'
    }

    def __init__(self, client_id, client_secret, access_token=None, refresh_token=None, mashape_key=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth = None
        self.mashape_key = mashape_key

        if refresh_token is not None:
            self.auth = AuthWrapper(access_token, refresh_token, client_id, client_secret)

        self.credits = self.get_credits()

    def set_user_auth(self, access_token, refresh_token):
        self.auth = AuthWrapper(access_token, refresh_token, self.client_id, self.client_secret)

    def get_client_id(self):
        return self.client_id

    def get_credits(self):
        return self.make_request('GET', 'credits', None, True)

    def get_auth_url(self, response_type='pin'):
        return '%soauth2/authorize?client_id=%s&response_type=%s' % (API_URL, self.client_id, response_type)

    def authorize(self, response, grant_type='pin'):
        return self.make_request('POST', 'oauth2/token', {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': grant_type,
            'code' if grant_type == 'authorization_code' else grant_type: response
        }, True)

    def prepare_headers(self, force_anon=False):
        headers = {}
        if force_anon or self.auth is None:
            if self.client_id is None:
                raise ImgurClientError('Client credentials not found!')
            else:
                headers['Authorization'] = 'Client-ID %s' % self.get_client_id()
        else:
            headers['Authorization'] = 'Bearer %s' % self.auth.get_current_access_token()

        if self.mashape_key is not None:
            headers['X-Mashape-Key'] = self.mashape_key

        return headers


    def make_request(self, method, route, data=None, force_anon=False):
        method = method.lower()
        method_to_call = getattr(requests, method)

        header = self.prepare_headers(force_anon)
        url = (MASHAPE_URL if self.mashape_key is not None else API_URL) + ('3/%s' % route if 'oauth2' not in route else route)

        if method in ('delete', 'get'):
            response = method_to_call(url, headers=header, params=data, data=data)
        else:
            response = method_to_call(url, headers=header, data=data)

        if response.status_code == 403 and self.auth is not None:
            self.auth.refresh()
            header = self.prepare_headers()
            if method in ('delete', 'get'):
                response = method_to_call(url, headers=header, params=data, data=data)
            else:
                response = method_to_call(url, headers=header, data=data)

        self.credits = {
            'UserLimit': response.headers.get('X-RateLimit-UserLimit'),
            'UserRemaining': response.headers.get('X-RateLimit-UserRemaining'),
            'UserReset': response.headers.get('X-RateLimit-UserReset'),
            'ClientLimit': response.headers.get('X-RateLimit-ClientLimit'),
            'ClientRemaining': response.headers.get('X-RateLimit-ClientRemaining')
        }

        # Rate-limit check
        if response.status_code == 429:
            raise ImgurClientRateLimitError()

        try:
            response_data = response.json()
        except:
            raise ImgurClientError('JSON decoding of response failed.')

        if 'data' in response_data and isinstance(response_data['data'], dict) and 'error' in response_data['data']:
            raise ImgurClientError(response_data['data']['error'], response.status_code)

        return response_data['data'] if 'data' in response_data else response_data

    def validate_user_context(self, username):
        if username == 'me' and self.auth is None:
            raise ImgurClientError('\'me\' can only be used in the authenticated context.')

    def logged_in(self):
        if self.auth is None:
            raise ImgurClientError('Must be logged in to complete request.')

    # Account-related endpoints
    def get_account(self, username):
        self.validate_user_context(username)
        account_data = self.make_request('GET', 'account/%s' % username)

        return Account(
            account_data['id'],
            account_data['url'],
            account_data['bio'],
            account_data['reputation'],
            account_data['created'],
            account_data['pro_expiration'],
        )

    def get_gallery_favorites(self, username, page=0):
        self.validate_user_context(username)
        gallery_favorites = self.make_request('GET', 'account/%s/gallery_favorites/%d' % (username, page))

        return build_gallery_images_and_albums(gallery_favorites)

    def get_account_favorites(self, username, page=0):
        self.validate_user_context(username)
        favorites = self.make_request('GET', 'account/%s/favorites/%d' % (username, page))

        return build_gallery_images_and_albums(favorites)

    def get_account_submissions(self, username, page=0):
        self.validate_user_context(username)
        submissions = self.make_request('GET', 'account/%s/submissions/%d' % (username, page))

        return build_gallery_images_and_albums(submissions)

    def get_account_settings(self, username):
        self.logged_in()
        settings = self.make_request('GET', 'account/%s/settings' % username)

        return AccountSettings(
            settings['email'],
            settings['high_quality'],
            settings['public_images'],
            settings['album_privacy'],
            settings['pro_expiration'],
            settings['accepted_gallery_terms'],
            settings['active_emails'],
            settings['messaging_enabled'],
            settings['blocked_users']
        )

    def change_account_settings(self, username, fields):
        post_data = {setting: fields[setting] for setting in set(self.allowed_account_fields).intersection(fields.keys())}
        return self.make_request('POST', 'account/%s/settings' % username, post_data)

    def get_email_verification_status(self, username):
        self.logged_in()
        self.validate_user_context(username)
        return self.make_request('GET', 'account/%s/verifyemail' % username)

    def send_verification_email(self, username):
        self.logged_in()
        self.validate_user_context(username)
        return self.make_request('POST', 'account/%s/verifyemail' % username)

    def get_account_albums(self, username, page=0):
        self.validate_user_context(username)

        albums = self.make_request('GET', 'account/%s/albums/%d' % (username, page))
        return [Album(album) for album in albums]

    def get_account_album_ids(self, username, page=0):
        self.validate_user_context(username)
        return self.make_request('GET', 'account/%s/albums/ids/%d' % (username, page))

    def get_account_album_count(self, username):
        self.validate_user_context(username)
        return self.make_request('GET', 'account/%s/albums/count' % username)

    def get_account_comments(self, username, sort='newest', page=0):
        self.validate_user_context(username)
        comments = self.make_request('GET', 'account/%s/comments/%s/%s' % (username, sort, page))

        return [Comment(comment) for comment in comments]

    def get_account_comment_ids(self, username, sort='newest', page=0):
        self.validate_user_context(username)
        return self.make_request('GET', 'account/%s/comments/ids/%s/%s' % (username, sort, page))

    def get_account_comment_count(self, username):
        self.validate_user_context(username)
        return self.make_request('GET', 'account/%s/comments/count' % username)

    def get_account_images(self, username, page=0):
        self.validate_user_context(username)
        images = self.make_request('GET', 'account/%s/images/%d' % (username, page))

        return [Image(image) for image in images]

    def get_account_image_ids(self, username, page=0):
        self.validate_user_context(username)
        return self.make_request('GET', 'account/%s/images/ids/%d' % (username, page))

    def get_account_images_count(self, username):
        self.validate_user_context(username)
        return self.make_request('GET', 'account/%s/images/count' % username)

    # Album-related endpoints
    def get_album(self, album_id):
        album = self.make_request('GET', 'album/%s' % album_id)
        return Album(album)

    def get_album_images(self, album_id):
        images = self.make_request('GET', 'album/%s/images' % album_id)
        return [Image(image) for image in images]

    def create_album(self, fields):
        post_data = {field: fields[field] for field in set(self.allowed_album_fields).intersection(fields.keys())}

        if 'ids' in post_data:
            self.logged_in()

        return self.make_request('POST', 'album', data=post_data)

    def update_album(self, album_id, fields):
        post_data = {field: fields[field] for field in set(self.allowed_album_fields).intersection(fields.keys())}

        if isinstance(post_data['ids'], list):
            post_data['ids'] = ','.join(post_data['ids'])

        return self.make_request('POST', 'album/%s' % album_id, data=post_data)

    def album_delete(self, album_id):
        return self.make_request('DELETE', 'album/%s' % album_id)

    def album_favorite(self, album_id):
        self.logged_in()
        return self.make_request('POST', 'album/%s/favorite' % album_id)

    def album_set_images(self, album_id, ids):
        if isinstance(ids, list):
            ids = ','.join(ids)

        return self.make_request('POST', 'album/%s/' % album_id, {'ids': ids})

    def album_add_images(self, album_id, ids):
        if isinstance(ids, list):
            ids = ','.join(ids)

        return self.make_request('POST', 'album/%s/add' % album_id, {'ids': ids})

    def album_remove_images(self, album_id, ids):
        if isinstance(ids, list):
            ids = ','.join(ids)

        return self.make_request('DELETE', 'album/%s/remove_images' % album_id, {'ids': ids})

    # Comment-related endpoints
    def get_comment(self, comment_id):
        comment = self.make_request('GET', 'comment/%d' % comment_id)
        return Comment(comment)

    def delete_comment(self, comment_id):
        self.logged_in()
        return self.make_request('DELETE', 'comment/%d' % comment_id)

    def get_comment_replies(self, comment_id):
        replies = self.make_request('GET', 'comment/%d/replies' % comment_id)
        return format_comment_tree(replies)

    def post_comment_reply(self, comment_id, image_id, comment):
        self.logged_in()
        data = {
            'image_id': image_id,
            'comment': comment
        }

        return self.make_request('POST', 'comment/%d' % comment_id, data)

    def comment_vote(self, comment_id, vote='up'):
        self.logged_in()
        return self.make_request('POST', 'comment/%d/vote/%s' % (comment_id, vote))

    def comment_report(self, comment_id):
        self.logged_in()
        return self.make_request('POST', 'comment/%d/report' % comment_id)

    # Custom Gallery Endpoints
    def get_custom_gallery(self, gallery_id, sort='viral', window='week', page=0):
        gallery = self.make_request('GET', 'g/%s/%s/%s/%s' % (gallery_id, sort, window, page))
        return CustomGallery(
            gallery['id'],
            gallery['name'],
            gallery['datetime'],
            gallery['account_url'],
            gallery['link'],
            gallery['tags'],
            gallery['item_count'],
            gallery['items']
        )

    def get_user_galleries(self):
        self.logged_in()
        galleries = self.make_request('GET', 'g')

        return [CustomGallery(
            gallery['id'],
            gallery['name'],
            gallery['datetime'],
            gallery['account_url'],
            gallery['link'],
            gallery['tags']
        ) for gallery in galleries]

    def create_custom_gallery(self, name, tags=None):
        self.logged_in()
        data = {'name': name}

        if tags:
            data['tags'] = ','.join(tags)

        gallery = self.make_request('POST', 'g', data)

        return CustomGallery(
            gallery['id'],
            gallery['name'],
            gallery['datetime'],
            gallery['account_url'],
            gallery['link'],
            gallery['tags']
        )

    def custom_gallery_update(self, gallery_id, name):
        self.logged_in()
        data = {
            'id': gallery_id,
            'name': name
        }

        gallery = self.make_request('POST', 'g/%s' % gallery_id, data)

        return CustomGallery(
            gallery['id'],
            gallery['name'],
            gallery['datetime'],
            gallery['account_url'],
            gallery['link'],
            gallery['tags']
        )

    def custom_gallery_add_tags(self, gallery_id, tags):
        self.logged_in()

        if tags:
            data = {'tags': ','.join(tags)}
        else:
            raise ImgurClientError('tags must not be empty!')

        return self.make_request('PUT', 'g/%s/add_tags' % gallery_id, data)

    def custom_gallery_remove_tags(self, gallery_id, tags):
        self.logged_in()

        if tags:
            data = {'tags': ','.join(tags)}
        else:
            raise ImgurClientError('tags must not be empty!')

        return self.make_request('DELETE', 'g/%s/remove_tags' % gallery_id, data)

    def custom_gallery_delete(self, gallery_id):
        self.logged_in()
        return self.make_request('DELETE', 'g/%s' % gallery_id)

    def filtered_out_tags(self):
        self.logged_in()
        return self.make_request('GET', 'g/filtered_out')

    def block_tag(self, tag):
        self.logged_in()
        return self.make_request('POST', 'g/block_tag', data={'tag': tag})

    def unblock_tag(self, tag):
        self.logged_in()
        return self.make_request('POST', 'g/unblock_tag', data={'tag': tag})

    # Gallery-related endpoints
    def gallery(self, section='hot', sort='viral', page=0, window='day', show_viral=True):
        if section == 'top':
            response = self.make_request('GET', 'gallery/%s/%s/%s/%d?showViral=%s'
                                                % (section, sort, window, page, str(show_viral).lower()))
        else:
            response = self.make_request('GET', 'gallery/%s/%s/%d?showViral=%s'
                                                % (section, sort, page, str(show_viral).lower()))

        return build_gallery_images_and_albums(response)

    def memes_subgallery(self, sort='viral', page=0, window='week'):
        if sort == 'top':
            response = self.make_request('GET', 'g/memes/%s/%s/%d' % (sort, window, page))
        else:
            response = self.make_request('GET', 'g/memes/%s/%d' % (sort, page))

        return build_gallery_images_and_albums(response)

    def memes_subgallery_image(self, item_id):
        item = self.make_request('GET', 'g/memes/%s' % item_id)
        return build_gallery_images_and_albums(item)

    def subreddit_gallery(self, subreddit, sort='time', window='week', page=0):
        if sort == 'top':
            response = self.make_request('GET', 'gallery/r/%s/%s/%s/%d' % (subreddit, sort, window, page))
        else:
            response = self.make_request('GET', 'gallery/r/%s/%s/%d' % (subreddit, sort, page))

        return build_gallery_images_and_albums(response)

    def subreddit_image(self, subreddit, image_id):
        item = self.make_request('GET', 'gallery/r/%s/%s' % (subreddit, image_id))
        return build_gallery_images_and_albums(item)

    def gallery_tag(self, tag, sort='viral', page=0, window='week'):
        if sort == 'top':
            response = self.make_request('GET', 'gallery/t/%s/%s/%s/%d' % (tag, sort, window, page))
        else:
            response = self.make_request('GET', 'gallery/t/%s/%s/%d' % (tag, sort, page))

        return Tag(
            response['name'],
            response['followers'],
            response['total_items'],
            response['following'],
            response['items']
        )

    def gallery_tag_image(self, tag, item_id):
        item = self.make_request('GET', 'gallery/t/%s/%s' % (tag, item_id))
        return build_gallery_images_and_albums(item)

    def gallery_item_tags(self, item_id):
        response = self.make_request('GET', 'gallery/%s/tags' % item_id)

        return [TagVote(
            item['ups'],
            item['downs'],
            item['name'],
            item['author']
        ) for item in response['tags']]

    def gallery_tag_vote(self, item_id, tag, vote):
        self.logged_in()
        response = self.make_request('POST', 'gallery/%s/vote/tag/%s/%s' % (item_id, tag, vote))
        return response

    def gallery_search(self, q, advanced=None, sort='time', window='all', page=0):
        if advanced:
            data = {field: advanced[field]
                    for field in set(self.allowed_advanced_search_fields).intersection(advanced.keys())}
        else:
            data = {'q': q}

        response = self.make_request('GET', 'gallery/search/%s/%s/%s' % (sort, window, page), data)
        return build_gallery_images_and_albums(response)

    def gallery_random(self, page=0):
        response = self.make_request('GET', 'gallery/random/random/%d' % page)
        return build_gallery_images_and_albums(response)

    def share_on_imgur(self, item_id, title, terms=0):
        self.logged_in()
        data = {
            'title': title,
            'terms': terms
        }

        return self.make_request('POST', 'gallery/%s' % item_id, data)

    def remove_from_gallery(self, item_id):
        self.logged_in()
        return self.make_request('DELETE', 'gallery/%s' % item_id)

    def gallery_item(self, item_id):
        response = self.make_request('GET', 'gallery/%s' % item_id)
        return build_gallery_images_and_albums(response)

    def report_gallery_item(self, item_id):
        self.logged_in()
        return self.make_request('POST', 'gallery/%s/report' % item_id)

    def gallery_item_vote(self, item_id, vote='up'):
        self.logged_in()
        return self.make_request('POST', 'gallery/%s/vote/%s' % (item_id, vote))

    def gallery_item_comments(self, item_id, sort='best'):
        response = self.make_request('GET', 'gallery/%s/comments/%s' % (item_id, sort))
        return format_comment_tree(response)

    def gallery_comment(self, item_id, comment):
        self.logged_in()
        return self.make_request('POST', 'gallery/%s/comment' % item_id, {'comment': comment})

    def gallery_comment_ids(self, item_id):
        return self.make_request('GET', 'gallery/%s/comments/ids' % item_id)

    def gallery_comment_count(self, item_id):
        return self.make_request('GET', 'gallery/%s/comments/count' % item_id)

    # Image-related endpoints
    def get_image(self, image_id):
        image = self.make_request('GET', 'image/%s' % image_id)
        return Image(image)

    def upload_from_path(self, path, config=None, anon=True):
        if not config:
            config = dict()

        fd = open(path, 'rb')
        contents = fd.read()
        b64 = base64.b64encode(contents)
        data = {
            'image': b64,
            'type': 'base64',
        }
        data.update({meta: config[meta] for meta in set(self.allowed_image_fields).intersection(config.keys())})
        fd.close()
        
        return self.make_request('POST', 'upload', data, anon)

    def upload_from_url(self, url, config=None, anon=True):
        if not config:
            config = dict()

        data = {
            'image': url,
            'type': 'url',
        }

        data.update({meta: config[meta] for meta in set(self.allowed_image_fields).intersection(config.keys())})
        return self.make_request('POST', 'upload', data, anon)

    def delete_image(self, image_id):
        return self.make_request('DELETE', 'image/%s' % image_id)

    def favorite_image(self, image_id):
        self.logged_in()
        return self.make_request('POST', 'image/%s/favorite' % image_id)

    # Conversation-related endpoints
    def conversation_list(self):
        self.logged_in()

        conversations = self.make_request('GET', 'conversations')
        return [Conversation(
            conversation['id'],
            conversation['last_message_preview'],
            conversation['datetime'],
            conversation['with_account_id'],
            conversation['with_account'],
            conversation['message_count'],
        ) for conversation in conversations]

    def get_conversation(self, conversation_id, page=1, offset=0):
        self.logged_in()

        conversation = self.make_request('GET', 'conversations/%d/%d/%d' % (conversation_id, page, offset))
        return Conversation(
            conversation['id'],
            conversation['last_message_preview'],
            conversation['datetime'],
            conversation['with_account_id'],
            conversation['with_account'],
            conversation['message_count'],
            conversation['messages'],
            conversation['done'],
            conversation['page']
        )

    def create_message(self, recipient, body):
        self.logged_in()
        return self.make_request('POST', 'conversations/%s' % recipient, {'body': body})

    def delete_conversation(self, conversation_id):
        self.logged_in()
        return self.make_request('DELETE', 'conversations/%d' % conversation_id)

    def report_sender(self, username):
        self.logged_in()
        return self.make_request('POST', 'conversations/report/%s' % username)

    def block_sender(self, username):
        self.logged_in()
        return self.make_request('POST', 'conversations/block/%s' % username)

    # Notification-related endpoints
    def get_notifications(self, new=True):
        self.logged_in()
        response = self.make_request('GET', 'notification', {'new': str(new).lower()})
        return build_notifications(response)

    def get_notification(self, notification_id):
        self.logged_in()
        response = self.make_request('GET', 'notification/%d' % notification_id)
        return build_notification(response)

    def mark_notifications_as_read(self, notification_ids):
        self.logged_in()
        return self.make_request('POST', 'notification', ','.join(notification_ids))

    # Memegen-related endpoints
    def default_memes(self):
        response = self.make_request('GET', 'memegen/defaults')
        return [Image(meme) for meme in response]
