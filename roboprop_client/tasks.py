from celery import shared_task
from roboprop_client.utils import (
    add_blenderkit_model_to_my_models,
    add_blenderkit_model_metadata,
)


@shared_task
def add_blenderkit_model_to_my_models_task(
    folder_name, asset_base_id, thumbnail, index
):
    try:
        response = add_blenderkit_model_to_my_models(
            folder_name, asset_base_id, thumbnail
        )
        if response.status_code == 201:
            metadata_response = add_blenderkit_model_metadata(
                folder_name, asset_base_id, index
            )
            return metadata_response.json()
        return response.status_code
    except Exception as e:
        # Handle exceptions as needed
        return str(e)
