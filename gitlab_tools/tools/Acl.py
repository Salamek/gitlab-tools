from functools import wraps

from flask import jsonify
from typing import List
from gitlab_tools.models.gitlab_tools import Role, User


class Acl(object):

    @staticmethod
    def roles_to_list(roles: List[Role]) -> List[int]:
        ret = []
        for role in roles:
            ret.append(role.id)
        return ret

    @staticmethod
    def get_user_roles(user: User) -> List[int]:
        roles = Acl.roles_to_list(user.roles)
        if not user.is_authenticated():
            roles.append(Role.GUEST)

        return roles

    @staticmethod
    def validate_path(allowed: List[int], user: User):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not set(Acl.get_user_roles(user)).isdisjoint(allowed):
                    # continue
                    return f(*args, **kwargs)
                else:
                    # Unauthorized
                    return jsonify({'message': 'Unauthorized access (Wrong API token)'}), 401

            return decorated_function

        return decorator

    @staticmethod
    def validate(allowed: List[int], user: User) -> bool:
        return not set(Acl.roles_to_list(user.roles)).isdisjoint(allowed)
