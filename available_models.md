# Available Models

Topaz Labs offers two different general classes of AI models:

## Model Classes

- **Standard**: These models are incredibly fast and efficient, and preserve the original fidelity and details of source images with maximum accuracy. Recommended for most professional use cases.
- **Generative**: These models can produce the highest quality and most creative outputs, at the cost of speed and fidelity to the original image. Recommended for most creative use cases.

> **Note**: Generative models are only available as asynchronous endpoints since these powerful models can take up to several minutes to complete; blocking a HTTP request for extended periods of time is not recommended.

---

## Enhance

These are our industry-standard upscaling and image enhancement models, which run blazingly fast and work great for most scenarios.

> Each of the models listed below are of the **Standard** class. None of these models are generative or diffusion-based.

### Standard Enhance Models

| Model | Description | Parameters |
|-------|-------------|------------|
| **Standard V2** | General-purpose model balancing detail, sharpness, and noise reduction for various images. | `sharpen`, `denoise`, `fix_compression` |
| **Low Resolution V2** | Enhances clarity and detail in low-resolution images like web graphics and screenshots. | `sharpen`, `denoise`, `fix_compression` |
| **CGI** | Optimized for CGI and digital illustrations, enhancing texture and detail in computer-generated images. | `sharpen`, `denoise` |
| **High Fidelity V2** | Ideal for high-quality images, preserving intricate details in professional photography. | `sharpen`, `denoise`, `fix_compression` |
| **Text Refine** | Designed for images with text and shapes, enhancing clarity and sharpness of elements. | `strength`, `sharpen`, `denoise`, `fix_compression` |

### Standard Enhance Parameters

- **`sharpen`**: Slightly sharpens the image. *(decimal from 0 to 1)*
- **`denoise`**: Reduces noise in the image. *(decimal from 0 to 1)*
- **`fix_compression`**: Reduces compression artifacts to improve details. *(decimal from 0 to 1)*
- **`strength`**: Controls model strength. Too high of a result can make results look unrealistic *(decimal from 0.01 to 1)*

> **Implementation Note**: These parameters should be appended as key-value fields in the form-data request bodies (i.e. alongside the `model`, `output_height`, and `face_enhancement` etc. fields). Any parameters not explicitly provided are automatically configured by our auto-parameter model. Extra parameters provided that are not supported are ignored.

---

## Enhance Generative

Our latest cutting-edge and most powerful generative AI models which can repair, reconstruct, and enhance your images. **These models only run asynchronously.**

> **Note**: These Generative models may produce creative outputs under certain scenarios. If you're looking for more consistent generations, you may consider our class of Standard models.

### Generative Enhance Models

| Model | Description | Parameters |
|-------|-------------|------------|
| **Redefine** | Elevate creativity with realistic upscaling, prioritizing either fidelity or creative detail. Ideal for low-resolution, blurry, and AI-generated images. | `prompt`, `autoprompt`, `creativity`, `texture`, `sharpen`, `denoise` |
| **Recovery** | Delivers high fidelity upscaling for extremely low-resolution images, preserving natural detail and sharpness. | `detail` |
| **Recovery V2** | Newest model that delivers high fidelity upscaling for extremely low-resolution images, preserving natural detail and sharpness. | `detail` |

### Generative Enhance Parameters

- **`prompt`**: A description of the resulting image you are looking for. The model responds more to a descriptive statement versus a directive one. 
  - Example: Use *"girl with red hair and blue eyes"* instead of *"change the girl's hair to red and make her eyes blue"*
  - *(text - max 1024 characters)*
- **`autoprompt`**: Whether you want to use our state-of-the-art autoprompting model to auto-generate a prompt for you. If enabled, ignores value given to prompt. *(boolean)*
- **`creativity`**: Lower creativity values maintain the highest fidelity to the original image. Higher values take more liberties and provide more creative results for specific details. *(integer from 1 to 6)*
- **`texture`**: Add texture to the image. Recommend setting texture to 1 for at a low creativity level, and 3 for more creative results at a higher creativity level. *(integer from 1 to 5)*
- **`sharpen`**: Slightly sharpens the image. *(decimal from 0 to 1)*
- **`denoise`**: Reduces noise in the image. *(decimal from 0 to 1)*
- **`detail`**: Adjusts the level of added detail after rendering. *(decimal from 0 to 1)*

---

## Sharpen

You can use the Sharpen models to create crisp, sharp image outputs, removing blur and bringing the subject or entire image into focus.

> All of the Sharpen models listed below are **Standard** type models, and are not generative.

### Standard Sharpen Models

| Model | Description | Parameters |
|-------|-------------|------------|
| **Standard** | All-purpose sharpening, intended for images with slight amounts of lens and motion blur. | `strength`, `minor_denoise` |
| **Strong** | For very blurry and out-of-focus images. Try the Standard model before the Strong model to avoid over sharpening and generating unwanted artifacts. | `strength` |
| **Lens Blur** | Ideal for images affected by imperfections caused when the camera lens fails to focus correctly. | `strength`, `minor_denoise` |
| **Lens Blur V2** | Generation 2 of the Lens Blur model, producing more consistent and stronger sharpening results in most scenarios. | `strength`, `minor_denoise` |
| **Motion Blur** | Optimized to correct the streaked or smeared effect caused by the movement of either the camera or the subject during the exposure time. | `strength`, `minor_denoise` |
| **Natural** | Designed to sharpen objects and keep textures looking natural. | `strength`, `minor_denoise` |
| **Refocus** | Emphasize details and bring out finer lines or texture. | `strength`, `minor_denoise` |

### Standard Sharpen Parameters

- **`strength`**: Increases details. Too much sharpening can create an unrealistic result. *(decimal from 0.01 to 1)*
- **`minor_denoise`**: Removes noisy pixels to increase clarity. Can slightly increase image sharpness. *(decimal from 0.01 to 1)*

---

## Sharpen Generative

A more powerful version of Sharpening using generative AI to add back missing information when refocusing and sharpening an image.

> **Note**: Under some scenarios, these models may be Generative as compared to our Standard sharpening models.

### Generative Sharpen Models

| Model | Description | Parameters |
|-------|-------------|------------|
| **Super Focus** | Fix blur and extract detail on the most stubborn and difficult images that cannot be enhanced through other sharpening models. | `strength`, `focus_boost`, `seed` |
| **Super Focus V2** | Our newest model that fixes blur and extract detail on the most stubborn and difficult images that cannot be enhanced through other sharpening models. | `detail`, `focus_boost` |

### Generative Sharpen Parameters

- **`strength`**: Increases details. Too much sharpening can create an unrealistic result. *(decimal from 0 to 1)*
- **`detail`**: Increases details. Too much sharpening can create an unrealistic result. *(decimal from 0 to 1)*
  - > **Note**: 'Strength' was renamed to 'Detail' in Super Focus V2
- **`focus_boost`**: Use on very blurry images! Focus boost corrects images that are missing detail by downscaling your image then upscaling the results back to the original size. *(decimal from 0.25 to 1)*
- **`seed`**: Generation seed. *(integer from -2147483648 to 2147483647)*

---

## Denoise

Remove sensor noise and grain from images, creating crisp and smooth details. Does wonders especially for low-light or RAW images. Under some scenarios, these models can even be used to remove dust and splotches on an image.

> All of these models are **Standard** class models, and are not Generative.

### Denoise Models

| Model | Description | Parameters |
|-------|-------------|------------|
| **Normal** | Ideal to remove low-medium noise caused by low-light conditions or compression artifacts, usually for images from smartphones and cameras with their own denoise models to avoid over-processing. | `strength`, `minor_deblur`, `original_detail` |
| **Strong** | Designed to strongly emphasize retaining image detail for medium-high noise images. Use it for images from very low-light conditions. | `strength`, `minor_deblur`, `original_detail` |
| **Extreme** | Prioritizes removing as much noise as possible rather than preserving detail. Use it for images with severe noise or heavy compression, such as those shared over the internet. | `strength`, `minor_deblur`, `original_detail` |

### Denoise Parameters

- **`strength`**: Reduces noise in the image. Too high can remove detail and slightly blur the image. *(decimal from 0.01 to 1)*
- **`minor_deblur`**: Slightly sharpens the image. Counteracts softness caused by noise reduction. *(decimal from 0.01 to 1)*
- **`original_detail`**: Return texture and fine details lost during noise reduction. Start at low values and slowly increase. *(decimal from 0 to 1)*

---

## Restore Generative

Revive your sentimental, aged photos with our restorative models. Designed to bring your old images back to life, these models retain the original look and feel of the image while breathing in new life.

> All of these models are **Generative** class models.

### Restore Models

| Model | Description | Parameters |
|-------|-------------|------------|
| **Dust-Scratch** | Heal major dust, scratches, and surface damage, while preserving the look of your original photos. Archival photos and less-than-pristine lenses are perfect use cases for this brand-new image enhancement—the first AI model of its kind. | None |

> **Note**: These parameters are automatically configured and do not require or accept any selection from the user.

---

## Lighting

Bring vibrance to your images shot in less-than-ideal lighting conditions. Our lighting models change the image on a pixel-by-pixel basis according to their unique characteristics and surrounding context instead of adjusting them universally.

> All of these models are **Standard** class models, and are not Generative.

### Lighting Models

| Model | Description | Parameters |
|-------|-------------|------------|
| **Adjust** | This filter modifies exposure and contrast to produce a well-lit and vibrant image. | `color_correction`, `exposure`, `highlight`, `shadow` |
| **White Balance** | This filter neutralizes unwanted color casts and allows creative tone adjustments through cooler and warmer enhancements. | `temperature`, `opacity` |

### Lighting Parameters

- **`color_correction`**: *(boolean of true or false)*
- **`exposure`**: *(decimal from 0 to 2)*
- **`highlight`**: *(decimal from 0 to 2)*
- **`shadow`**: *(decimal from 0 to 2)*
- **`temperature`**: *(decimal from 0.01 to 1)*
- **`opacity`**: *(decimal from 0.01 to 1)*

> **Note**: Any parameters that are not explicitly provided are automatically configured.