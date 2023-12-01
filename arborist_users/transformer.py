import json
from collections import defaultdict
from datetime import datetime

import yaml
from gen3users.validation import validate_user_yaml


def _resource_list(source: dict, destination: list) -> dict:
    """
    Recursively iterate through values, create {name, subresources} dictionary.
    """
    for key, value in source.items():
        if isinstance(value, dict):
            _ = {'name': key, 'subresources': []}
            destination.append(_)
            _resource_list(value, _['subresources'])
    return destination


def transform(context: str, directory: str = 'DATA') -> dict:
    """
    Transform arborist information into DATA/{context}/user.yaml file.

    \b
     see https://github.com/uc-cdis/fence/blob/master/docs/user.yaml_guide.md
    """
    clients = {'wts': {'policies': []}}
    authz = {'anonymous_policies': [], 'all_users_policies': [], 'groups': [], 'resources': [], 'policies': [],
             'roles': [], }
    user_yaml = {'clients': clients, 'authz': authz, 'users': []}

    with open(f"{directory}/{context}/resource.json", "r") as f:
        resources = json.load(f)['resources']
        # simplify the resources into a recursive dict
        simplified = defaultdict(defaultdict)
        for resource in resources:
            path_parts = [_ for _ in resource['path'].split('/') if _ != '']
            _ = simplified
            for part in path_parts:
                if part not in _:
                    _[part] = defaultdict(defaultdict)
                _ = _[part]

        # transform the simplified dict into a list of dicts
        simplified_resources = []
        _resource_list(simplified, simplified_resources)
        authz['resources'] = simplified_resources

    with open(f"{directory}/{context}/role.json", "r") as f:
        roles = json.load(f)['roles']
        authz['roles'] = roles

    with open(f"{directory}/{context}/policy.json", "r") as f:
        policies = json.load(f)['policies']
        authz['policies'] = policies

    with open(f"{directory}/{context}/group.json", "r") as f:
        groups = json.load(f)['groups']
        authz['groups'] = groups

    with open(f"{directory}/{context}/user.json", "r") as f:
        users = json.load(f)['users']
        users_dict = {_['name']: {'tags': _.get('tags', {}), 'policies': [p['policy'] for p in _['policies']]} for _ in
                      users}
        user_yaml['users'] = users_dict

    return user_yaml


def save(user_yaml: dict, context: str, directory: str) -> str:
    """Save user.yaml to {directory}/{context}/user.yaml"""
    file_name = f"{directory}/{context}/user.yaml"
    with open(file_name, "w") as f:
        print(f"# Created by arborist_users at {datetime.now()} from {context}", file=f)
        yaml.dump(data=user_yaml, stream=f, sort_keys=True)
    return file_name


def validate(file_name: str) -> None:
    with open(file_name, "r") as f:
        user_yaml = f.read()
        validate_user_yaml(user_yaml, file_name)
