from unittest.mock import Mock, patch
from my_project.core import do_something

@patch("my_project.core.requests.get")
def test_do_something(mock_get: Mock) -> None:
    mock_get.return_value.json.return_value = {"uuid": "fake-uuid"}
    assert do_something() == "fake-uuid"
    mock_get.assert_called_once_with(
        "https://httpbin.org/uuid", timeout=10
    )
