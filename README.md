
# Arborist Users

Utilities extract [Arborist](https://github.com/uc-cdis/arborist) data and transform it into a format that can be used by [Gen3]( https://github.com/uc-cdis/fence/blob/master/docs/user.yaml_guide.md)

## Dependencies

> kubectl and access to the gen3 cluster

## Installation

```

python3 -m venv venv ; source venv/bin/activate

pip install -r requirements.txt

pip install -e .

```

## Usage

```
arborist_users --help
Usage: arborist_users [OPTIONS] COMMAND [ARGS]...

  Use kubectl to extract arborist entities[resource, role, policy, etc.] from
  current k8s context.

Options:
  --help  Show this message and exit.

Commands:
  extract    Extract to DATA/{context}/{entity}.yaml
  transform  Transform arborist information into DATA/{context}/user.yaml...
  pods       Show information about current k8s context.
  ping       Verify kubectl and context.

```
