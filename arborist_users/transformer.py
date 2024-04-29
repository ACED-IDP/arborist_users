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
    Transform arborist information into DATA/{context}/user.yaml file filter out users and policies created by requestor.

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
        policies = [_ for _ in policies if _['description'] != 'policy created by requestor']
        authz['policies'] = policies

    admin_users = []
    with open(f"{directory}/{context}/group.json", "r") as f:
        groups = json.load(f)['groups']
        authz['groups'] = groups
        for _ in groups:
            if _['name'] == 'anonymous':
                authz['anonymous_policies'] = [p for p in _['policies']]
            if _['name'] == 'logged-in':
                authz['all_users_policies'] = [p for p in _['policies']]
            if _['name'] == 'administrators':
                admin_users = [u for u in _['users']]

    with open(f"{directory}/{context}/user.json", "r") as f:
        users = json.load(f)['users']
        users = [_ for _ in users if _['name'] in admin_users]
        users_dict = {
            _['name']: {
                'tags': _.get('tags', {}),
                'policies': [p['policy'] for p in _['policies'] if p['policy'] in policies]
            } for _ in users}
        user_yaml['users'] = users_dict

    return user_yaml


def transform_requestor(context: str, directory: str = 'DATA') -> dict:
    """
    Transform arborist information into DATA/{context}/requestor.yaml file filter out users and policies created by user.yaml.

    \b
     see https://github.com/uc-cdis/fence/blob/master/docs/user.yaml_guide.md
    """
    requestor_yaml = {'users': []}

    with open(f"{directory}/{context}/policy.json", "r") as f:
        policies = json.load(f)['policies']
        policies = [_ for _ in policies if _['description'] == 'policy created by requestor']
        requestor_yaml['policies'] = policies
    policy_ids = [p['id'] for p in policies]

    with open(f"{directory}/{context}/user.json", "r") as f:
        users = json.load(f)['users']
        users_with_no_policies = []
        users_dict = {
            _['name']: {
                'tags': _.get('tags', {}),
                'policies': sorted([p['policy'] for p in _['policies'] if p['policy'] in policy_ids])
            } for _ in users}
        for k, _ in users_dict.items():
            del users_dict[k]['tags']
            if not _['policies']:
                users_with_no_policies.append(k)
                continue

            policies = sorted([p for p in _['policies'] if p in policy_ids])

            resources = defaultdict(list)
            for _ in policies:
                policy_parts = _.split('.')
                writer_option = ''
                if 'writer' in _:
                    writer_option = ' --write'
                resource = f"/programs/{policy_parts[1]}/projects/{policy_parts[3].split('_')[0]}"
                cmd = f"g3t collaborator add {k} {resource} {writer_option} --approve"
                if [c for c in resources[resource] if 'write' in c]:
                    continue
                resources[resource].append(cmd)
            users_dict[k]['commands'] = dict(resources)
            del users_dict[k]['policies']

        del requestor_yaml['policies']

        for k in users_with_no_policies:
            del users_dict[k]

        requestor_yaml['users'] = users_dict
        commands = []
        for u, v in users_dict.items():
            for authz, cmds in v['commands'].items():
                if len(cmds) > 1:
                    for c in cmds:
                        if 'write' in c:
                            commands.append(c)
                            break
                else:
                    commands.append(cmds[0])
    return commands


def save_user_yaml(user_yaml: dict, context: str, directory: str) -> str:
    """Save user.yaml to {directory}/{context}/user.yaml"""
    file_name = f"{directory}/{context}/user.yaml"
    with open(file_name, "w") as f:
        print(f"# Created by arborist_users at {datetime.now()} from {context}", file=f)
        yaml.dump(data=user_yaml, stream=f, sort_keys=True)
    return file_name


def save_requestor_sh(requestor_yaml: dict, context: str, directory: str) -> str:
    """Save requestor.shto {directory}/{context}/requestor.yaml"""
    file_name = f"{directory}/{context}/requestor.sh"
    with open(file_name, "w") as f:
        print(f"# Created by arborist_users at {datetime.now()} from {context}", file=f)
        for _ in requestor_yaml:
            print(_, file=f)
        # yaml.dump(data=requestor_yaml, stream=f, sort_keys=True)
    return file_name


def validate(file_name: str) -> None:
    with open(file_name, "r") as f:
        user_yaml = f.read()
        validate_user_yaml(user_yaml, file_name)
