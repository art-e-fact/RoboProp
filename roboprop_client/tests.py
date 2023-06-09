from unittest.mock import patch, Mock
from django.test import TestCase
from roboprop_client.views import _get_models, _get_roboprop_model_thumbnails
from roboprop_client.utils import unflatten_dict


class ViewsTestCase(TestCase):
    def test_get_models(self):
        mock_response = Mock()
        mock_response.json.return_value = {
            "resource": [
                {"type": "folder", "name": "model1"},
                {"type": "file", "name": "file1"},
            ]
        }
        with patch(
            "roboprop_client.views._make_get_request", return_value=mock_response
        ):
            models = _get_models("https://example.com/api/")
            self.assertEqual(models, ["model1"])

    def test_get_roboprop_model_thumbnails(self):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resource": [{"path": "/path/to/thumbnail.png"}]
        }
        mock_content = b"example content"
        with patch(
            "roboprop_client.views._make_get_request", return_value=mock_response
        ), patch(
            "roboprop_client.views.base64.b64encode", return_value=b"example base64"
        ), patch(
            "roboprop_client.views._make_get_request.content", return_value=mock_content
        ):
            thumbnails = _get_roboprop_model_thumbnails(["model1"])
            self.assertEqual(
                thumbnails, [{"name": "model1", "image": "example base64"}]
            )


class UtilsTestCase(TestCase):
    def test_unflatten_dict(self):
        flat_dict = {
            "model.name": "Cessna C-172",
            "model.version": "1.0",
            "model.sdf.@version": "1.5",
            "model.sdf.#text": "model.sdf",
        }
        nested_dict = unflatten_dict(flat_dict)
        self.assertEqual(
            nested_dict,
            {
                "model": {
                    "name": "Cessna C-172",
                    "version": "1.0",
                    "sdf": {"@version": "1.5", "#text": "model.sdf"},
                }
            },
        )
