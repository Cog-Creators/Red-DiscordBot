class Message(object):

    def __init__(self, message_id, from_user, account_id, sender_id, body, conversation_id, datetime):
        self.id = message_id
        self.from_user = from_user
        self.account_id = account_id
        self.sender_id = sender_id
        self.body = body
        self.conversation_id = conversation_id
        self.datetime = datetime
