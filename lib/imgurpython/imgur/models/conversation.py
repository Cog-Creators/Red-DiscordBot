from .message import Message

class Conversation(object):

    def __init__(self, conversation_id, last_message_preview, datetime, with_account_id, with_account, message_count, messages=None,
                 done=None, page=None):
        self.id = conversation_id
        self.last_message_preview = last_message_preview
        self.datetime = datetime
        self.with_account_id = with_account_id
        self.with_account = with_account
        self.message_count = message_count
        self.page = page
        self.done = done

        if messages:
            self.messages = [Message(
                message['id'],
                message['from'],
                message['account_id'],
                message['sender_id'],
                message['body'],
                message['conversation_id'],
                message['datetime'],
            ) for message in messages]
        else:
            self.messages = None
