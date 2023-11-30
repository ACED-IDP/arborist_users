import json
import pathlib
import subprocess
import sys
from datetime import datetime

import click
import yaml
from gen3users.validation import validate_user_yaml


class NaturalOrderGroup(click.Group):
    """Allow listing Commands in order of appearance, with common parameters.

    See https://github.com/pallets/click/issues/513 """

    def list_commands(self, ctx):
        """Commands in order of appearance"""
        return self.commands.keys()


def _run_command(command: str, shell: bool = False) -> str:
    """Run a command and return the output as a string"""
    results = subprocess.run(command.split(), capture_output=True, shell=shell)
    return results.stdout.decode('utf-8').strip()


def _get_context() -> str:
    """Get the current k8s context"""
    raw_context = _run_command("kubectl config current-context")
    return raw_context.split("/")[-1]


def _get_pods() -> dict:
    """Get the pods"""
    return json.loads(_run_command("kubectl get pods -o json"))


def _get_pod(pod_name: str, pods: dict) -> dict:
    """Get the current"""
    for pod in pods['items']:
        if pod['metadata']['name'].startswith(pod_name):
            return pod
    return None


def _save_arborist_configurations(context: str, pod_name: str) -> None:
    resource_names = ['user', 'resource', 'role', 'policy', 'group']
    print(f"Retrieving resources from {pod_name}, saving to DATA/{context}")
    pathlib.Path(f"DATA/{context}").mkdir(parents=True, exist_ok=True)
    for resource_name in resource_names:
        cmd = f"kubectl exec --stdin --tty  {pod_name}  -- curl -s http://localhost/{resource_name}"
        resources = _run_command(cmd)
        assert json.loads(resources), f"Failed to retrieve {resource_name} from arborist"
        file_name = f"DATA/{context}/{resource_name}.json"
        with open(file_name, "w") as f:
            f.write(resources)
        print(f"  Saved {resource_name}.json")


@click.group(cls=NaturalOrderGroup)
def cli():
    """Use kubectl to extract arborist entities[resource, role, policy, etc.] from current k8s context."""
    pass


@cli.command('extract')
def extract():
    """Extract to DATA/{context}/{entity}.yaml"""
    context = _get_context()
    print(f"Retrieving arborist information from context: {context}")

    pods = _get_pods()
    arborist = _get_pod("arborist-deployment", pods)
    container_statuses = arborist.get('status', {}).get('containerStatuses', [])
    ready = all([_.get('ready', False) for _ in container_statuses])
    state = list([list(_.get('state', {}).keys())[0] for _ in container_statuses])[0]
    if ready:
        pathlib.Path(f"DATA/{context}").mkdir(parents=True, exist_ok=True)
        _save_arborist_configurations(context, arborist['metadata']['name'])
    else:
        print(f"  {arborist['metadata']['name']} is not ready. state: {state}")

@cli.command('transform')
def transform():
    """
    Transform arborist information into DATA/{context}/user.yaml file.

    \b
    See https://github.com/uc-cdis/fence/blob/master/docs/user.yaml_guide.md
    """
    context = _get_context()
    print(f"Transforming arborist information from k8s context: {context}")
    clients = {'wts': {'policies': []}}
    authz = {'anonymous_policies': [], 'all_users_policies': [], 'groups': [], 'resources': [], 'policies': [],
             'roles': [], }
    user_yaml = {'clients': clients, 'authz': authz, 'users': []}

    with open(f"DATA/{context}/resource.json", "r") as f:
        resources = json.load(f)['resources']
        for resource in resources:
            # validate will append subresources to the resource
            resource['name'] = resource['path'].replace('/', '', 1)
            # subresources is a list of strings, should be a list of dicts
            fixed = []
            for sub_resource in resource.get('subresources', []):
                if isinstance(sub_resource, str):
                    sub_resource = {'name': sub_resource}
                fixed.append(sub_resource)
                resource['subresources'] = fixed
        authz['resources'] = resources

    with open(f"DATA/{context}/role.json", "r") as f:
        roles = json.load(f)['roles']
        authz['roles'] = roles

    with open(f"DATA/{context}/policy.json", "r") as f:
        policies = json.load(f)['policies']
        authz['policies'] = policies

    with open(f"DATA/{context}/group.json", "r") as f:
        groups = json.load(f)['groups']
        authz['groups'] = groups

    with open(f"DATA/{context}/user.json", "r") as f:
        users = json.load(f)['users']
        users_dict = {_['name']: {'tags': _.get('tags', {}), 'policies': [p['policy'] for p in _['policies']]} for _ in
                      users}
        user_yaml['users'] = users_dict

    # see https://github.com/uc-cdis/fence/blob/master/docs/user.yaml_guide.md
    file_name = f"DATA/{context}/user.yaml"
    with open(file_name, "w") as f:
        print(f"# Created by arborist_users at {datetime.now()} from {context}", file=f)
        yaml.dump(data=user_yaml, stream=f, sort_keys=True)
        print(f"  Saved {file_name}")

    with open(file_name, "r") as f:
        user_yaml = f.read()
        validate_user_yaml(user_yaml, file_name)
        print(f"  Validated {file_name}")


@cli.command('pods')
def ping():
    """Show information about current k8s context."""
    pods = _get_pods()
    pod_summaries = {}
    warnings = []
    for _ in pods['items']:
        app = _.get('metadata', {}).get('labels', {}).get('app', '')
        name = _.get('metadata', {}).get('name', '')
        if app == '':
            app = name
        container_statuses = _.get('status', {}).get('containerStatuses', [])
        ready = all([_.get('ready', False) for _ in container_statuses])
        state = list([list(_.get('state', {}).keys())[0] for _ in container_statuses])[0]
        image = list(set([_.get('image', None) for _ in container_statuses]))[0]
        if state == 'terminated':
            continue
        if not ready:
            warnings.append(f"{name} is not ready. state: {state}")
            continue
        if state != 'running':
            warnings.append(f"{name} is not running. state: {state}")
            continue
        if app not in pod_summaries:
            pod_summaries[app] = {'name': name, 'image': image}
        else:
            warnings.append(f"Duplicate app name: {app} {pod_summaries[app]} {name}")
            current = pod_summaries[app]
            pod_summaries[app] = {'names': current['name'], 'image': image}

    print(yaml.dump({'pods': pod_summaries, 'warnings': warnings}, sort_keys=True))


@cli.command('ping')
def ping():
    """Verify kubectl and context."""
    context = _get_context()
    kubectl_version = json.loads(_run_command(f"kubectl version --output=json"))
    kubectl_client_version = f"{kubectl_version['clientVersion']['major']}.{kubectl_version['clientVersion']['minor']}"

    print(yaml.dump({'kubectl': kubectl_client_version, 'context': context}, sort_keys=False))


if __name__ == "__main__":
    cli()
