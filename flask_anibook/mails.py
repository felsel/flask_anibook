from flask import url_for
from flask_mail import Message

from flask_anibook import mail


def send_reset_username(user):
    msg = Message("flask_anibook: Forgotten username")
    msg.add_recipient(f"{user['email']}")
    msg.body = f"We received a request for your username.\nIn our record the username assiciated to this email is:\n{user['user_name']}."
    mail.send(msg)


def send_reset_password(user, token):
    msg = Message("flask_anibook: Password reset request.")
    msg.add_recipient(f"{user['email']}")
    msg.body = f"""To reset your password, visit the following link:
    {url_for('auth.verified_reset', token=token, _external=True)}
    If you did not make this request then simply ignore this email and no change will be made
    """
    mail.send(msg)
