class Account(object):

    def __init__(self, account_id, url, bio, reputation, created, pro_expiration):
        self.id = account_id
        self.url = url
        self.bio = bio
        self.reputation = reputation
        self.created = created
        self.pro_expiration = pro_expiration
