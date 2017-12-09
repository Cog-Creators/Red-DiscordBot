class Notification(object):

    def __init__(self, notification_id, account_id, viewed, content):
        self.id = notification_id
        self.account_id = account_id
        self.viewed = viewed
        self.content = content
