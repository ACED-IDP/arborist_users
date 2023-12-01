import pytest
import yaml

from arborist_users.transformer import save, validate


@pytest.fixture
def directory():
    """Return a directory."""
    return 'tests/fixtures'


@pytest.fixture
def context():
    """Return a context."""
    return 'mock-extracted'


@pytest.fixture
def expected_user_yaml(directory: str, context: str):
    return yaml.safe_load(open(f"{directory}/{context}/expected-user.yaml", "r"))


def test_transform(directory: str, context: str, expected_user_yaml: dict):
    """Test transform."""
    from arborist_users.transformer import transform
    user_yaml = transform(context, directory=directory)
    assert user_yaml is not None
    assert user_yaml['clients'] is not None
    assert user_yaml['authz'] is not None
    assert user_yaml['users'] is not None
    assert user_yaml['authz']['resources'] is not None
    assert user_yaml['authz']['roles'] is not None
    assert user_yaml['authz']['policies'] is not None
    assert user_yaml['authz']['groups'] is not None
    assert user_yaml['users'] is not None

    # save(user_yaml, context, directory)
    # return

    for k in ['resources', 'roles', 'policies', 'groups']:
        assert user_yaml['authz'][k] == expected_user_yaml['authz'][k], f"{k} is not equal expected_user_yaml"

    for k in ['clients', 'users']:
        assert user_yaml[k] == expected_user_yaml[k], f"{k} is not equal expected_user_yaml"

    file_name = save(user_yaml, context, directory)
    validate(file_name)
