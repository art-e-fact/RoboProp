from unittest.mock import patch, Mock
from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache
from django.contrib.auth.models import User
from roboprop_client.views import _get_models, _get_model_thumbnails, _search_and_cache
from roboprop_client.utils import unflatten_dict, flatten_dict


class UserTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse("register")

    def test_register_new_user_success(self):
        data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "testpassword",
            "password_confirm": "testpassword",
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.filter(username="testuser").exists())

    def test_register_password_mismatch(self):
        data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "testpassword",
            "password_confirm": "mismatchedpassword",
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Passwords do not match")
        self.assertFalse(User.objects.filter(username="testuser").exists())

    def test_register_invalid_data(self):
        data = {
            "username": "",
            "email": "invalidemail",
            "password": "testpassword",
            "password_confirm": "testpassword",
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Error creating user")
        self.assertFalse(User.objects.filter(username="").exists())


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
            thumbnails = _get_model_thumbnails(["model1"], "folder1")
            self.assertEqual(
                thumbnails,
                [{"name": "model1", "image": "example base64", "folder": "folder1"}],
            )

    @patch("roboprop_client.views._get_model_thumbnails")
    @patch("roboprop_client.views._get_model_configuration")
    def test_mymodel_detail(
        self, mock_get_model_configuration, mock_get_model_thumbnails
    ):
        # Set up mock data for _get_roboprop_model_thumbnails
        mock_thumbnail = {"image": "thumbnail.jpg", "folder": "folder1"}
        mock_get_model_thumbnails.return_value = [mock_thumbnail]
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


class SearchAndCacheTestCase(TestCase):
    @patch("roboprop_client.views.requests.get")
    def test_search_and_cache_with_cache_hit(self, mock_get):
        # Set up the cache
        cache_key = "search_results_test"
        search_results = [{"name": "test_model"}]
        cache.set(cache_key, search_results)

        # Call the function
        result = _search_and_cache("test")

        # Check the result
        self.assertEqual(result, search_results)

        # Check that requests.get() was not called
        mock_get.assert_not_called()

        # Clean up the cache
        cache.delete(cache_key)

    @patch("roboprop_client.views.requests.get")
    def test_search_and_cache_with_cache_miss(self, mock_get):
        # Set up the mock response
        mock_response = Mock()
        mock_response.json.return_value = [{"name": "test_model"}]
        mock_get.return_value = mock_response

        # Call the function
        result = _search_and_cache("test")

        # Check the result
        expected_result = [{"name": "test_model"}]
        self.assertEqual(result, expected_result)

        # Check that requests.get() was called with the correct URL
        expected_url = "https://fuel.gazebosim.org/1.0/models?q=test"
        mock_get.assert_called_once_with(expected_url)

        # Check that the search results were cached
        cache_key = "search_results_test"
        cached_result = cache.get(cache_key)
        self.assertEqual(cached_result, expected_result)


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
