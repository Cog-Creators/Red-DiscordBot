class AccountSettings(object):

    def __init__(self, email, high_quality, public_images, album_privacy, pro_expiration, accepted_gallery_terms,
                 active_emails, messaging_enabled, blocked_users):
        self.email = email
        self.high_quality = high_quality
        self.public_images = public_images
        self.album_privacy = album_privacy
        self.pro_expiration = pro_expiration
        self.accepted_gallery_terms = accepted_gallery_terms
        self.active_emails = active_emails
        self.messaging_enabled = messaging_enabled
        self.blocked_users = blocked_users
