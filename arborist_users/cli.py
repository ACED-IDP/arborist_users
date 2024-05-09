import json

import click
import yaml

from arborist_users import _get_context, _get_pods, _run_command
from arborist_users.extractor import extract
from arborist_users.transformer import transform, validate, save_user_yaml, transform_requestor, save_requestor_sh


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

    file_name = save_user_yaml(user_yaml, context, directory)
    print(f"  Saved {file_name}")

    validate(file_name)
    print(f"  Validated {file_name}")

    requestor_yaml = transform_requestor(context, directory=directory)
    file_name = save_requestor_sh(requestor_yaml, context, directory)
    print(f"  Saved {file_name}")


@cli.command('validate')
@click.argument('path', type=click.Path(exists=True), required=True)
def _validate(path: str):
    """Validate user.yaml file."""
    try:
        validate(path)
        print(f"  Validated {path}")
    except Exception as e:
        print(f"  {e}")


@cli.command('ping')
def _ping():
    """Verify kubectl and context."""
    context = _get_context()
    kubectl_version = json.loads(_run_command("kubectl version --output=json"))
    kubectl_client_version = f"{kubectl_version['clientVersion']['major']}.{kubectl_version['clientVersion']['minor']}"

    print(yaml.dump({'kubectl': kubectl_client_version, 'context': context}, sort_keys=False))


if __name__ == "__main__":
    cli()
