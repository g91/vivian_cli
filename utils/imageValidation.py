"""Port of src/utils/imageValidation.ts."""
from __future__ import annotations

from typing import Any, Dict, List

from ..constants.apiLimits import API_IMAGE_MAX_BASE64_SIZE
from ..services.analytics.index import logEvent
from .format import format_bytes


OversizedImage = Dict[str, Any]


class ImageSizeError(Exception):
    """Error thrown when one or more images exceed the API size limit."""

    def __init__(self, oversizedImages: List[OversizedImage], maxSize: int) -> None:
        first_image = oversizedImages[0] if oversizedImages else None
        if len(oversizedImages) == 1 and first_image:
            message = (
                f"Image base64 size ({format_bytes(first_image['size'])}) exceeds API limit "
                f"({format_bytes(maxSize)}). Please resize the image before sending."
            )
        else:
            message = (
                f"{len(oversizedImages)} images exceed the API limit ({format_bytes(maxSize)}): "
                + ", ".join(
                    f"Image {image['index']}: {format_bytes(image['size'])}"
                    for image in oversizedImages
                )
                + ". Please resize these images before sending."
            )
        super().__init__(message)
        self.name = "ImageSizeError"
        self.oversizedImages = oversizedImages
        self.maxSize = maxSize


def isBase64ImageBlock(block):
    """Type guard to check if a block is a base64 image block"""
    if not isinstance(block, dict):
        return False
    if block.get("type") != "image":
        return False
    source = block.get("source")
    if not isinstance(source, dict):
        return False
    return source.get("type") == "base64" and isinstance(source.get("data"), str)


def validateImagesForAPI(messages):
    """Validates that all images in messages are within the API size limit.
This is a safety net at the API boundary to catch any oversized images
that may have slipped through upstream processing.

Note: The API's 5MB limit applies to the base64-encoded string length,
not the decoded raw bytes.

Works with both UserMessage/AssistantMessage types (which have { type, message })
and raw MessageParam types (which have { role, content }).

@param messages - Array of messages to validate
@throws ImageSizeError if any image exceeds the API limit"""
    oversized_images: List[OversizedImage] = []
    image_index = 0

    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        if msg.get("type") != "user":
            continue

        inner_message = msg.get("message")
        if not isinstance(inner_message, dict):
            continue

        content = inner_message.get("content")
        if isinstance(content, str) or not isinstance(content, list):
            continue

        for block in content:
            if not isBase64ImageBlock(block):
                continue
            image_index += 1
            base64_size = len(block["source"]["data"])
            if base64_size > API_IMAGE_MAX_BASE64_SIZE:
                logEvent(
                    "tengu_image_api_validation_failed",
                    {
                        "base64_size_bytes": base64_size,
                        "max_bytes": API_IMAGE_MAX_BASE64_SIZE,
                    },
                )
                oversized_images.append({"index": image_index, "size": base64_size})

    if oversized_images:
        raise ImageSizeError(oversized_images, API_IMAGE_MAX_BASE64_SIZE)


is_base64_image_block = isBase64ImageBlock
validate_images_for_api = validateImagesForAPI

