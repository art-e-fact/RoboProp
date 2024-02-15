from celery import shared_task
from roboprop_client.utils import (
    _add_blenderkit_model_to_my_models,
    _add_blenderkit_model_metadata,
)


@shared_task
def add_blenderkit_model_to_my_models_task(
    request, folder_name, asset_base_id, thumbnail, index
):
    try:
        response = _add_blenderkit_model_to_my_models(
            folder_name, asset_base_id, thumbnail
        )
        if response.status_code == 201:
            metadata_response = _add_blenderkit_model_metadata(
                request, folder_name, asset_base_id, index
            )
            return metadata_response
        return response.status_code
    except Exception as e:
        # Handle exceptions as needed
        return str(e)
