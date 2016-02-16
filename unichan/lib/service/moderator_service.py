import string

import bcrypt
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound

from unichan.database import get_db
from unichan.lib import ArgumentError
from unichan.lib import roles
from unichan.lib.models import Moderator, Report, Post, Thread, Board
from unichan.lib.models.board import board_moderator_table
from unichan.lib.utils import now


class ModeratorService:
    USERNAME_MAX_LENGTH = 50
    USERNAME_ALLOWED_CHARS = string.ascii_letters + string.digits + '_'
    PASSWORD_MIN_LENGTH = 6
    PASSWORD_MAX_LENGTH = 50
    PASSWORD_ALLOWED_CHARS = string.ascii_letters + string.digits + string.punctuation + '_'

    def __init__(self, cache):
        self.cache = cache

    def add_report(self, report):
        db = get_db()

        exiting_report = None
        try:
            exiting_report = db.query(Report).filter_by(post_id=report.post_id).one()
        except NoResultFound:
            pass

        if exiting_report is not None:
            exiting_report.count += 1
        else:
            report.count = 1
            db.add(report)

        report.date = now()

        db.commit()

    def get_reports(self, moderator):
        db = get_db()

        reports_query = db.query(Report)
        # Show all reports when the moderator has the admin role
        if not self.has_role(moderator, roles.ROLE_ADMIN):
            # Filter that gets all reports for the moderator id
            reports_query = reports_query.filter(Report.post_id == Post.id, Post.thread_id == Thread.id,
                                                 Thread.board_id == Board.id, Board.id == board_moderator_table.c.board_id,
                                                 board_moderator_table.c.moderator_id == moderator.id)

        reports_query = reports_query.order_by(desc(Report.date))
        reports = reports_query.all()

        return reports

    def can_delete(self, moderator, post):
        if self.has_role(moderator, roles.ROLE_ADMIN):
            return True
        else:
            return self.moderates_board(moderator, post.thread.board)

    def check_username_validity(self, username):
        if not 0 < len(username) <= self.USERNAME_MAX_LENGTH:
            return False

        if not all(c in self.USERNAME_ALLOWED_CHARS for c in username):
            return False

        return True

    def check_password_validity(self, password):
        if password is None or len(password) < self.PASSWORD_MIN_LENGTH or len(password) >= self.PASSWORD_MAX_LENGTH:
            return False

        if not all(c in self.PASSWORD_ALLOWED_CHARS for c in password):
            return False

        return True

    def create_moderator(self, moderator, password):
        if not self.check_username_validity(moderator.username):
            raise ArgumentError('Invalid username')

        if not self.check_password_validity(password):
            raise ArgumentError('Invalid password')

        moderator.password = self.hash_password(password)

        db = get_db()
        db.add(moderator)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise ArgumentError('Duplicate username')

    def delete_moderator(self, moderator):
        db = get_db()
        db.delete(moderator)
        db.commit()

    def find_moderator_id(self, id):
        db = get_db()
        try:
            return db.query(Moderator).filter_by(id=id).one()
        except NoResultFound:
            return None

    def find_moderator_username(self, username):
        db = get_db()
        try:
            return db.query(Moderator).filter_by(username=username).one()
        except NoResultFound:
            return None

    def get_all_moderators(self):
        return get_db().query(Moderator).all()

    def role_exists(self, role):
        return role is not None and role in roles.ALL_ROLES

    def has_role(self, moderator, role):
        return role is not None and role in moderator.roles

    def add_role(self, moderator, role):
        if not self.role_exists(role):
            raise ArgumentError('Invalid role')

        moderator.roles.append(role)

        db = get_db()
        db.commit()

    def remove_role(self, moderator, role):
        if not role:
            raise ArgumentError('Invalid role')

        if not self.has_role(moderator, role):
            raise ArgumentError('Role not on moderator')

        moderator.roles.remove(role)

        db = get_db()
        db.commit()

    def moderates_board(self, moderator, board):
        return board in moderator.boards

    def change_password(self, moderator, old_password, new_password):
        if not self.check_password_validity(old_password):
            raise ArgumentError('Invalid password')

        self.check_password(moderator, old_password)

        self._update_password(moderator, new_password)

    def change_password_admin(self, moderator, new_password):
        self._update_password(moderator, new_password)

    def check_password(self, moderator, password):
        moderator_hashed_password = moderator.password

        if bcrypt.hashpw(password.encode(), moderator_hashed_password) != moderator_hashed_password:
            raise ArgumentError('Password does not match')

    def hash_password(self, password):
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    def _update_password(self, moderator, new_password):
        if not self.check_password_validity(new_password):
            raise ArgumentError('Invalid new password')

        moderator.password = self.hash_password(new_password)

        db = get_db()
        db.commit()
