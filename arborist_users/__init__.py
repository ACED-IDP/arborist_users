import json
import subprocess


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
    """Get pod_name from pods"""
    for pod in pods['items']:
        if pod['metadata']['name'].startswith(pod_name):
            return pod
    return None
