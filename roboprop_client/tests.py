from django.test import TestCase
from django.urls import reverse
import unittest
from unittest.mock import patch, MagicMock
from roboprop_client.views import (
    _get_models,
    _get_roboprop_model_thumbnails,
    mymodel_detail,
)

"""mocks cheat sheet and the equivalent commands that they mock:
mock_response == requests.get(url, headers=headers)
mock_response.json() == response.json()
mock_get.return_value is returned instead of making actual http request
"""


class TestGetModels(unittest.TestCase):
    @patch("roboprop_client.views.requests.get")
    def test_get_models_roboprop(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"resource": ["model1", "model2"]}
        mock_get.return_value = mock_response

        result = _get_models("roboprop")

        self.assertEqual(result, ["model1", "model2"])


class TestGetRobopropModelThumbnails(unittest.TestCase):
    @patch("roboprop_client.views.requests.get")
    def test_returns_list_of_dictionaries(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = b"thumbnail"
        mock_get.return_value = mock_response

        models = [
            ".gitignore",
            "model1/thumbnails/1.png",
            "model2/thumbnails/2.png",
            "model2/thumbnails/3.png",
            "model2/4.png",
            "model2/5.png",
        ]

        result = _get_roboprop_model_thumbnails(models)

        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], dict)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "model1")
        self.assertEqual(result[1]["name"], "model2")

    @patch("roboprop_client.views.requests.get")
    def test_returns_correct_thumbnail(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = b"thumbnail"
        mock_get.return_value = mock_response

        models = [
            ".gitignore",
            "model1/thumbnails/1.png",
            "model1/thumbnails/2.png",
            "model2/thumbnails/3.png",
            "model2/4.png",
            "model2/5.png",
        ]

        result = _get_roboprop_model_thumbnails(models)

        self.assertEqual(result[0]["name"], "model1")
        self.assertEqual(result[0]["image"], "dGh1bWJuYWls")
        self.assertEqual(result[1]["name"], "model2")
        self.assertEqual(result[1]["image"], "dGh1bWJuYWls")


class MyModelDetailTestCase(TestCase):
    def test_model_detail(self):
        model_name = "example_model"
        url = reverse("mymodel_detail", args=[model_name])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, model_name)
