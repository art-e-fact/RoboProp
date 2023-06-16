from unittest.mock import patch, Mock
from django.test import TestCase
from roboprop_client.views import _get_models, _get_roboprop_model_thumbnails
from roboprop_client.utils import unflatten_dict, flatten_dict


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
        mock_response.content = b"example content"
        with patch(
            "roboprop_client.views._make_get_request", return_value=mock_response
        ), patch(
            "roboprop_client.views.base64.b64encode", return_value=b"example base64"
        ):
            thumbnails = _get_roboprop_model_thumbnails(["model1"], "folder1")
            self.assertEqual(
                thumbnails,
                [{"name": "model1", "image": "example base64", "folder": "folder1"}],
            )

    @patch("roboprop_client.views._get_roboprop_model_thumbnails")
    @patch("roboprop_client.views._get_model_configuration")
    def test_mymodel_detail(
        self, mock_get_model_configuration, mock_get_roboprop_model_thumbnails
    ):
        # Set up mock data for _get_roboprop_model_thumbnails
        mock_thumbnail = {"image": "thumbnail.jpg", "folder": "folder1"}
        mock_get_roboprop_model_thumbnails.return_value = [mock_thumbnail]
        # Set up mock data for _get_model_configuration
        mock_configuration = {"name": "My Model", "version": "1.0"}
        mock_get_model_configuration.return_value = mock_configuration
        # Set up mock data for the request
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"example content"
        with patch(
            "roboprop_client.views._make_get_request", return_value=mock_response
        ):
            # Make a request to mymodel_detail
            response = self.client.get("/mymodels/folder1/MyModel/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Model")
        self.assertContains(response, "thumbnail.jpg")
        self.assertContains(response, "1.0")


"""
At present, unflatten_dict and flatten_dict are designed to be used with
model.config files, i.e for metadata, where a huge amount of nesting / 
complexity is not expected. If it comes to a point of also wanting to 
support full on sdf models and worlds, these tests will want to be more
thorough.
"""


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

    def test_flatten_dict(self):
        nested_dict = {
            "model": {
                "name": "Cessna C-172",
                "version": "1.0",
                "sdf": {"@version": "1.5", "#text": "model.sdf"},
            }
        }
        flat_dict = flatten_dict(nested_dict)
        self.assertEqual(
            flat_dict,
            {
                "model.name": "Cessna C-172",
                "model.version": "1.0",
                "model.sdf.@version": "1.5",
                "model.sdf.#text": "model.sdf",
            },
        )
