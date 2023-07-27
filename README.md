# RoboProp

## Installation

* [Installation Wiki Page](https://github.com/art-e-fact/RoboProp/wiki/installation)

### Development

* Styling: Tailwind and Flowbite

### Calling and Using Models

Models can be called directly from the fileserver with the following url:

```
Headers: X-DreamFactory-Api-Key: {YOUR_FILESERVER_APP_API_KEY}
GET: {FILESERVER_URL}/files/models/{MODEL_NAME}/?zip=true
```
An example curl request:

```
curl -X GET "http://18.183.51.71/api/v2/files/models/TintinRocket/?zip=true"  -H "X-DreamFactory-API-Key: {API_KEY_HERE}" -o myfilename.zip
```

Note that the downloaded zip will include the parent folder "models" so you will need to move over the model_name directory to your simulator assets path.

#### Fuel Models

Models added from Fuel will extract in the regular "fuel" manner and so can be called with `model.sdf` e.g in the case of Gazebo
```
<model name="my_model">
    <include>
        <uri>models://my_model_name/model.sdf</uri>
    </include>
    <pose>0 0 0 0 0 0</pose>
</model>
```

### Blendkit Models

Blendkit models upon selection are converted to sdf format before being uploaded to the fileserver, and (at present) two mesh objects are provided, `.obj` (the default) and `.glb` (which stores more information about model shaders, but is incompatible with gazebo). As a result, there will be two `sdf` files (and two `config` files) created. Make sure to call the correct one based on your simulator:

* `model.sdf` (which will reference the .obj mesh)
* `gltf-model.sdf` (which will reference the .glb mesh)