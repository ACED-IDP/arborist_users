
# Arborist Users

Utilities extract [Arborist](https://github.com/uc-cdis/arborist) data and transform it into a format that can be used by [Gen3]( https://github.com/uc-cdis/fence/blob/master/docs/user.yaml_guide.md)

## Use case

* As a devops engineer or DAC member, in order to review current state of projects, users, policies and roles, I need to see a high fidelity document that details current state.   Up until now, that has been the user.yaml document.
* As a devops engineer, in order to restore current state of projects, users, policies and roles, I need to snapshot state, move the artifact from one environment(development, testing, staging, production) to another and apply that state to the new environment.   Up until now, that has been the user.yaml document.

Since we have adopted a [requestor](https://github.com/uc-cdis/requestor/blob/master/docs/functionality_and_flow.md) based flow, this “snapshot state” ability is missing

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
  extract    Extract to DATA/{context}/{entity}.json
  transform  Transform arborist information into DATA/{context}/user.yaml...
  validate   Validate user.yaml file.
  ping       Verify kubectl and context.

```
