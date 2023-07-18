import roboprop_client.utils as utils
from unittest.mock import patch, Mock
from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from roboprop_client.views import (
    _get_assets,
    _get_thumbnails,
    _search_and_cache,
)


class RegisterUserTestCase(TestCase):
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


class LoginUserTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse("login")
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpassword"
        )

    def test_login_view_success(self):
        data = {
            "username": "testuser",
            "password": "testpassword",
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home"))

    def test_login_view_invalid_credentials(self):
        data = {
            "username": "testuser",
            "password": "wrongpassword",
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid credentials")

    def tearDown(self):
        self.user.delete()


class UserSettingsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpassword"
        )
        self.client.login(username="testuser", password="testpassword")
        self.user_settings_url = reverse("user_settings")

    def test_user_settings_view_success(self):
        data = {
            "username": "newusername",
            "email": "newemail@example.com",
            "current_password": "testpassword",
            "new_password": "newpassword",
            "new_password_confirm": "newpassword",
        }
        response = self.client.post(self.user_settings_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.user_settings_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your account has been updated!")
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "newusername")
        self.assertEqual(self.user.email, "newemail@example.com")
        self.assertTrue(self.user.check_password("newpassword"))

    def test_user_settings_view_incorrect_password(self):
        data = {
            "username": "newusername",
            "email": "newemail@example.com",
            "current_password": "wrongpassword",
            "new_password": "newpassword",
            "new_password_confirm": "newpassword",
        }
        response = self.client.post(self.user_settings_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.user_settings_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Incorrect password.")
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "testuser")
        self.assertEqual(self.user.email, "testuser@example.com")
        self.assertTrue(self.user.check_password("testpassword"))

    def test_user_settings_view_no_changes(self):
        data = {
            "username": "",
            "email": "",
            "current_password": "testpassword",
            "new_password": "",
            "new_password_confirm": "",
        }
        response = self.client.post(self.user_settings_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.user_settings_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Nothing to change.")
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "testuser")
        self.assertEqual(self.user.email, "testuser@example.com")
        self.assertTrue(self.user.check_password("testpassword"))

    def test_user_settings_view_new_password_mismatch(self):
        data = {
            "username": "newusername",
            "email": "newemail@example.com",
            "current_password": "testpassword",
            "new_password": "newpassword",
            "new_password_confirm": "wrongpassword",
        }
        response = self.client.post(self.user_settings_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.user_settings_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "New Password does not match.")
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "testuser")
        self.assertEqual(self.user.email, "testuser@example.com")
        self.assertTrue(self.user.check_password("testpassword"))

    def tearDown(self):
        self.user.delete()


class ViewsTestCase(TestCase):
    def test_get_assets(self):
        mock_response = Mock()
        mock_response.json.return_value = {
            "resource": [
                {"type": "folder", "name": "model1"},
                {"type": "file", "name": "file1"},
            ]
        }
        with patch(
            "roboprop_client.utils.make_get_request", return_value=mock_response
        ):
            models = _get_assets("https://example.com/api/")
            self.assertEqual(models, ["model1"])

    def test_get_asset_thumbnails(self):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resource": [{"path": "/path/to/thumbnail.png"}]
        }
        mock_response.content = b"example content"
        with patch(
            "roboprop_client.utils.make_get_request", return_value=mock_response
        ), patch(
            "roboprop_client.views.base64.b64encode", return_value=b"example base64"
        ):
            thumbnails = _get_thumbnails(["model1"], "models")
            self.assertEqual(
                thumbnails,
                [{"name": "model1", "image": "example base64"}],
            )

    @patch("roboprop_client.views._get_thumbnails")
    @patch("roboprop_client.views._get_model_configuration")
    def test_mymodel_detail(self, mock_get_model_configuration, mock_get_thumbnails):
        # Set up mock data for _get_roboprop_model_thumbnails
        mock_thumbnail = {"image": "thumbnail.jpg"}
        mock_get_thumbnails.return_value = [mock_thumbnail]
        # Set up mock data for _get_model_configuration
        mock_configuration = {"name": "My Model", "version": "1.0"}
        mock_get_model_configuration.return_value = mock_configuration
        # Set up mock data for the request
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"example content"
        with patch(
            "roboprop_client.utils.make_get_request", return_value=mock_response
        ):
            # Make a request to mymodel_detail
            response = self.client.get("/mymodels/MyModel/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Model")
        self.assertContains(response, "thumbnail.jpg")
        self.assertContains(response, "1.0")


class SearchAndCacheTestCase(TestCase):
    @patch("roboprop_client.views.__search_external_library")
    def test_search_and_cache(self, mock_search_external_library):
        # Set up the mock
        mock_search_external_library.return_value = {"result": "mocked"}

        # Call the function with a search term
        search_results = _search_and_cache("test")

        # Check that the mocks were called with the expected URLs
        mock_search_external_library.assert_any_call(
            "https://fuel.gazebosim.org/1.0/models?q=test", "fuel"
        )
        mock_search_external_library.assert_any_call(
            "https://www.blenderkit.com/api/v1/search/?query=search+text:test+asset_type:model+order:_score+is_free:True&page=1",
            "blendkit",
        )

        # Check that the search results were cached
        cache_key = "search_results_test"
        cached_results = cache.get(cache_key)
        self.assertIsNotNone(cached_results)
        self.assertEqual(cached_results["fuel"], {"result": "mocked"})
        self.assertEqual(cached_results["blendkit"], {"result": "mocked"})

        # Check that the function returned the cached results
        self.assertEqual(search_results, cached_results)


class MyModelsUploadTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("mymodels")
        self.file = SimpleUploadedFile("KitchenSink.zip", b"file_content")

    @patch("requests.post")
    def test_file_upload_success(self, mock_post):
        mock_post.return_value.status_code = 201
        response = self.client.post(self.url, {"file": self.file})
        self.assertRedirects(response, "/add-metadata/KitchenSink/")
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Model uploaded successfully")

    @patch("requests.post")
    def test_file_upload_failure(self, mock_post):
        mock_post.return_value.status_code = 400
        response = self.client.post(self.url, {"file": self.file})
        self.assertRedirects(response, self.url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Failed to upload model")


class AddToMyModelsTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("roboprop_client.views.__add_fuel_model_to_my_models")
    def test_add_fuel_model_to_my_models(self, mock_add_fuel_model_to_my_models):
        mock_add_fuel_model_to_my_models.return_value = Mock(status_code=201)
        response = self.client.post(
            "/add-to-my-models/",
            {"name": "test_model", "library": "fuel", "owner": "test_owner"},
        )
        # Confirm correct arguments
        mock_add_fuel_model_to_my_models.assert_called_once_with(
            "test_model", "test_owner"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {"message": "Success: Model: test_model added to My Models"},
        )

    @patch("roboprop_client.views.__add_blendkit_model_to_my_models")
    def test_add_blendkit_model_to_my_models(
        self, mock_add_blendkit_model_to_my_models
    ):
        mock_add_blendkit_model_to_my_models.return_value = Mock(status_code=400)
        response = self.client.post(
            "/add-to-my-models/",
            {
                "name": "test_model",
                "library": "blendkit",
                "assetBaseId": "test_asset_base_id",
                "thumbnail": "test_thumbnail",
            },
        )
        # Confirm correct arguments
        mock_add_blendkit_model_to_my_models.assert_called_once_with("test_thumbnail")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"error": "Failed to add model: test_model to My Models"},
        )

    def test_invalid_request_method(self):
        response = self.client.get("/add-to-my-models/")

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json(), {"error": "Invalid request method"})


"""
At present, flatten_dict is designed to be used with
model.config files, i.e for metadata, where a huge amount of nesting / 
complexity is not expected. If it comes to a point of also wanting to 
support full on sdf models and worlds, these tests will want to be more
thorough.
"""


class UtilsTestCase(TestCase):
    def test_flatten_dict(self):
        nested_dict = {
            "model": {
                "name": "Cessna C-172",
                "version": "1.0",
                "sdf": {"@version": "1.5", "#text": "model.sdf"},
            }
        }
        flat_dict = utils.flatten_dict(nested_dict)
        self.assertEqual(
            flat_dict,
            {
                "model.name": "Cessna C-172",
                "model.version": "1.0",
                "model.sdf.@version": "1.5",
                "model.sdf.#text": "model.sdf",
            },
        )

    def test_create_list_from_string(self):
        # Test with non-empty string
        assert utils.create_list_from_string("  apple,  banana,  cherry pie ") == [
            "apple",
            "banana",
            "cherry pie",
        ]
        assert utils.create_list_from_string("dog,cat") == ["dog", "cat"]
        assert utils.create_list_from_string("one,two,three") == ["one", "two", "three"]

        # Test with empty string
        assert utils.create_list_from_string("") == []
