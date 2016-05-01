# Helper methods for managing the moderator attached to the session

from flask import g as flaskg
from flask import session

from uchan import g
from uchan.lib import ArgumentError


def get_authed():
    return 'mod_auth_id' in session


def request_moderator():
    # Cache for the request
    if not hasattr(flaskg, 'authed_moderator'):
        if not get_authed():
            raise ArgumentError('Not authed')
        mod = g.moderator_service.find_moderator_id(session['mod_auth_id'])
        if mod is None:
            raise ArgumentError('Mod not found')

        flaskg.authed_moderator = mod
        return mod
    return flaskg.authed_moderator


def request_has_role(role):
    moderator = request_moderator()
    return moderator is not None and g.moderator_service.has_role(moderator, role)


def set_mod_authed(moderator):
    session['mod_auth_id'] = moderator.id


def unset_mod_authed():
    del session['mod_auth_id']
