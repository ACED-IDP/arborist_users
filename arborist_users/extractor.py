import json
import pathlib

from arborist_users import _run_command, _get_pods, _get_pod


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


def extract(context: str) -> None:
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
