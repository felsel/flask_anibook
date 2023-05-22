class UndetectedQueryError(Exception):
    "the query was not completed correctly"
    pass


class UsernameTaken(Exception):
    "username is already in the db"
    pass
