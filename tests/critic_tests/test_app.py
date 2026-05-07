import os

import pytest

from critic.app import app
from critic.libs.ddb import deserialize, get_client
from critic.tables import ProjectTable


os.environ.setdefault('CRITIC_NAMESPACE', 'test')


@pytest.fixture
def client():
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )
    with app.test_client() as client:
        yield client


def test_create_project_saves_to_ddb(client):
    resp = client.post('/create', data={'name': 'My Project'})

    assert resp.status_code == 302

    response = get_client().scan(TableName=ProjectTable.name())
    items = [deserialize(item) for item in response.get('Items', [])]

    print(items)

    assert len(items) == 1
    assert items[0]['name'] == 'My Project'
