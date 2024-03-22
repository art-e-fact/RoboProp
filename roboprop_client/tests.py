import roboprop_client.utils as utils
import json
from unittest.mock import patch, Mock, ANY
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from roboprop_client.views import (
    _get_assets,
    _get_thumbnails,
    _search_and_cache,
    add_to_my_models,
    mymodel_detail,
    mymodels,
)
from roboprop_client.tasks import add_blenderkit_model_to_my_models_task


class ViewsTestCase(TestCase):
    def setUp(self):
        self.mock_response = Mock()
        self.mock_response.status_code = 200

    def test_get_assets(self):
        self.mock_response.json.return_value = {
            "resource": [
                {"type": "folder", "name": "model1"},
                {"type": "file", "name": "file1"},
            ]
        }
        with patch(
            "roboprop_client.utils.make_get_request", return_value=self.mock_response
        ):
            models = _get_assets("https://example.com/api/")
            self.assertEqual(models, ["model1"])

    def test_get_asset_thumbnails(self):
        self.mock_response.json.return_value = {
            "resource": [{"path": "/path/to/thumbnail.png"}]
        }
        self.mock_response.content = b"example content"
        with patch(
            "roboprop_client.utils.make_get_request", return_value=self.mock_response
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

        with patch("roboprop_client.utils.make_get_request") as mock_make_get_request:
            self.mock_response.content = b"example content"
            mock_make_get_request.return_value = self.mock_response
            # Create request session to allow view to login
            factory = RequestFactory()
            request = factory.get("/mymodels/MyModel/")
            request.session = {}
            request.session["session_token"] = "dummy_token"
            response = mymodel_detail(request, "MyModel")

            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "My Model")
            self.assertContains(response, "thumbnail.jpg")
            self.assertContains(response, "1.0")


class SearchAndCacheTestCase(TestCase):
    @patch("roboprop_client.views._search_external_library")
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
            "https://www.blenderkit.com/api/v1/search/?query=search+text:test+asset_type:model+order:_score+is_free:False&page=1",
            "blenderkit",
        )

        # Check that the search results were cached
        cache_key = "search_results_test"
        cached_results = cache.get(cache_key)
        self.assertIsNotNone(cached_results)
        self.assertEqual(cached_results["fuel"], {"result": "mocked"})
        self.assertEqual(cached_results["blenderkit"], {"result": "mocked"})

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


# TODO: Fix from affecting index
# class AddToMyModelsTestCase(TestCase):
#     def setUp(self):
#         self.client = Client()
#         self.mock_response = Mock()
#         self.mock_response.status_code = 200
#         # Mock login to allow view tests to run
#         self.session = self.client.session
#         self.session["session_token"] = "dummy_token"
#         self.session.save()

#     @patch("roboprop_client.views._add_fuel_model_to_my_models")
#     @patch(
#         "roboprop_client.views._create_metadata_from_rekognition",
#         return_value=(
#             ["tag1", "tag2"],
#             ["category1", "category2"],
#             ["color1", "color2"],
#         ),
#     )
#     def test_add_fuel_model_to_my_models(
#         self, mock_detect_labels, mock_add_fuel_model_to_my_models
#     ):
#         with patch("roboprop_client.utils.make_get_request") as mock_make_get_request:
#             self.mock_response.content = json.dumps(
#                 {"index": "dummy_index"}
#             ).encode()  # Set the content to a JSON string
#             self.mock_response.json.return_value = {
#                 "resource": [{"path": "dummy_path"}]
#             }  # Make the Mock object behave like a dictionary
#             mock_make_get_request.return_value = self.mock_response
#             mock_add_fuel_model_to_my_models.return_value = Mock(status_code=201)
#             factory = RequestFactory()
#             request = factory.post(
#                 "/add-to-my-models/",
#                 {"name": "test_model", "library": "fuel", "owner": "test_owner"},
#             )
#             request.session = self.session
#             response = add_to_my_models(request)

#             # Confirm correct arguments
#             mock_add_fuel_model_to_my_models.assert_called_once_with(
#                 "test_model", "test_owner"
#             )

#             self.assertEqual(response.status_code, 201)
#             self.assertEqual(
#                 json.loads(response.content),
#                 {
#                     "message": "Success: Model: test_model added to My Models, and successfully tagged"
#                 },
#             )

#     @patch("roboprop_client.utils.make_get_request")
#     @patch.object(add_blenderkit_model_to_my_models_task, "delay")
#     def test_add_blenderkit_model_to_my_models(
#         self, mock_add_blenderkit_model_to_my_models, mock_make_get_request
#     ):
#         self.mock_response.content = json.dumps(
#             {"index": "dummy_index"}
#         ).encode()  # To JSON
#         mock_make_get_request.return_value = self.mock_response
#         mock_add_blenderkit_model_to_my_models.return_value = Mock(id="dummy_task_id")
#         factory = RequestFactory()
#         request = factory.post(
#             "/add-to-my-models/",
#             {
#                 "name": "test_model",
#                 "library": "blenderkit",
#                 "assetBaseId": "test_asset_base_id",
#                 "thumbnail": "test_thumbnail",
#             },
#         )
#         request.session = self.session
#         response = add_to_my_models(request)

#         # Confirm correct arguments
#         mock_add_blenderkit_model_to_my_models.assert_called_once_with(
#             "Test_model", "test_asset_base_id", "test_thumbnail", ANY
#         )

#         self.assertEqual(response.status_code, 202)
#         self.assertEqual(
#             json.loads(response.content),
#             {
#                 "task_id": "dummy_task_id",
#                 "message": "Blender to sdf conversion in progress...",
#             },
#         )

#     def test_invalid_request_method(self):
#         with patch("roboprop_client.utils.make_get_request") as mock_make_get_request:
#             mock_make_get_request.return_value = self.mock_response
#             factory = RequestFactory()
#             request = factory.get("/add-to-my-models/")
#             request.session = self.session
#             response = add_to_my_models(request)

#             self.assertEqual(response.status_code, 405)
#             self.assertEqual(
#                 json.loads(response.content), {"error": "Invalid request method"}
#             )


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
