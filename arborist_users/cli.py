import json

import click
import yaml

from arborist_users import _get_context, _get_pods, _run_command
from arborist_users.extractor import extract
from arborist_users.transformer import transform, save, validate


class NaturalOrderGroup(click.Group):
    """Allow listing Commands in order of appearance, with common parameters.

    See https://github.com/pallets/click/issues/513 """

    def list_commands(self, ctx):
        """Commands in order of appearance"""
        return self.commands.keys()


@click.group(cls=NaturalOrderGroup)
def cli():
    """Use kubectl to extract arborist entities[resource, role, policy, etc.] from current k8s context."""
    pass


@cli.command('extract')
def _extract():
    """Extract to DATA/{context}/{entity}.json"""
    context = _get_context()
    print(f"Retrieving arborist information from context: {context}")
    extract(context)


@cli.command('transform')
@click.option('--directory', default='DATA', help='Directory to save user.yaml', show_default=True)
def _transform(directory: str):
    """
    Transform arborist information into DATA/{context}/user.yaml file.

    \b
    See https://github.com/uc-cdis/fence/blob/master/docs/user.yaml_guide.md
    """
    context = _get_context()
    print(f"Transforming arborist information from k8s context: {context}")
    user_yaml = transform(context, directory=directory)

    file_name = save(user_yaml, context, directory)
    print(f"  Saved {file_name}")

    validate(file_name)
    print(f"  Validated {file_name}")


@cli.command('validate')
@click.option('--directory', default='DATA', help='Directory to save user.yaml', show_default=True)
def _validate(directory: str):
    try:
        file_name = f"{directory}/{_get_context()}/user.yaml"
        validate(file_name)
        print(f"  Validated {file_name}")
    except Exception as e:
        print(f"  {e}")


@cli.command('pods')
def _pods():
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
def _ping():
    """Verify kubectl and context."""
    context = _get_context()
    kubectl_version = json.loads(_run_command("kubectl version --output=json"))
    kubectl_client_version = f"{kubectl_version['clientVersion']['major']}.{kubectl_version['clientVersion']['minor']}"

    print(yaml.dump({'kubectl': kubectl_client_version, 'context': context}, sort_keys=False))


if __name__ == "__main__":
    cli()
