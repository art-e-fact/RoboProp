from django.test import TestCase
import unittest
from unittest.mock import patch, MagicMock
from roboprop_client.views import _get_assets, _get_roboprop_asset_thumbnails

"""mocks cheat sheet and the equivalent commands that they mock:
mock_response == requests.get(url, headers=headers)
mock_response.json() == response.json()
mock_get.return_value is returned instead of making actual http request
"""


class TestGetAssets(unittest.TestCase):
    @patch("roboprop_client.views.requests.get")
    def test_get_assets_roboprop(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"resource": ["asset1", "asset2"]}
        mock_get.return_value = mock_response

        result = _get_assets("roboprop")

        self.assertEqual(result, ["asset1", "asset2"])


class TestGetRobopropAssetThumbnails(unittest.TestCase):
    @patch("roboprop_client.views.requests.get")
    def test_returns_list_of_dictionaries(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = b"thumbnail"
        mock_get.return_value = mock_response

        assets = [
            ".gitignore",
            "model1/thumbnails/1.png",
            "model2/thumbnails/2.png",
            "model2/thumbnails/3.png",
            "model2/4.png",
            "model2/5.png",
        ]

        result = _get_roboprop_asset_thumbnails(assets)

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

        assets = [
            ".gitignore",
            "model1/thumbnails/1.png",
            "model1/thumbnails/2.png",
            "model2/thumbnails/3.png",
            "model2/4.png",
            "model2/5.png",
        ]

        result = _get_roboprop_asset_thumbnails(assets)

        self.assertEqual(result[0]["name"], "model1")
        self.assertEqual(result[0]["image"], "dGh1bWJuYWls")
        self.assertEqual(result[1]["name"], "model2")
        self.assertEqual(result[1]["image"], "dGh1bWJuYWls")
