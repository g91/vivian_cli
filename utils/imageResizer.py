"""Port of src/utils/imageResizer.ts

Image resizing and compression utilities using Pillow (PIL).
"""
from __future__ import annotations
import asyncio
import base64
import io
import struct
from typing import Any, Dict, Optional

API_IMAGE_MAX_BASE64_SIZE = 5 * 1024 * 1024
IMAGE_MAX_WIDTH = 8000
IMAGE_MAX_HEIGHT = 8000
IMAGE_TARGET_RAW_SIZE = 5 * 1024 * 1024

ImageMediaType = str
ImageDimensions = Dict[str, Any]
ResizeResult = Dict[str, Any]
ImageBlockWithDimensions = Dict[str, Any]
CompressedImageResult = Dict[str, Any]

ERROR_TYPE_MODULE_LOAD = 1
ERROR_TYPE_PROCESSING = 2
ERROR_TYPE_UNKNOWN = 3
ERROR_TYPE_PIXEL_LIMIT = 4
ERROR_TYPE_MEMORY = 5
ERROR_TYPE_TIMEOUT = 6
ERROR_TYPE_VIPS = 7
ERROR_TYPE_PERMISSION = 8


class ImageResizeError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.name = 'ImageResizeError'


def _format_file_size(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f'{n:.1f} {unit}'
        n /= 1024
    return f'{n:.1f} TB'


def _classify_image_error(error: Exception) -> int:
    msg = str(error).lower()
    if 'not available' in msg or 'import' in msg or 'module' in msg:
        return ERROR_TYPE_MODULE_LOAD
    if 'permission' in msg or 'eacces' in msg:
        return ERROR_TYPE_PERMISSION
    if 'memory' in msg or 'out of memory' in msg:
        return ERROR_TYPE_MEMORY
    if 'timeout' in msg or 'timed out' in msg:
        return ERROR_TYPE_TIMEOUT
    if 'pixel' in msg or 'dimensions' in msg:
        return ERROR_TYPE_PIXEL_LIMIT
    if 'corrupt' in msg or 'format' in msg or 'invalid' in msg:
        return ERROR_TYPE_PROCESSING
    return ERROR_TYPE_UNKNOWN


def _hash_string(s: str) -> int:
    h = 5381
    for c in s:
        h = ((h << 5) + h + ord(c)) & 0xFFFFFFFF
    return h


def _get_pil():
    try:
        from PIL import Image
        return Image
    except ImportError:
        raise ImportError('Native image processor module not available. Install Pillow: pip install Pillow')


def _resize_sync(image_buffer: bytes, original_size: int, ext: str) -> ResizeResult:
    try:
        Image = _get_pil()
        img = Image.open(io.BytesIO(image_buffer))
        fmt = (img.format or ext.lstrip('.')).lower()
        if fmt == 'jpg':
            fmt = 'jpeg'
        ow, oh = img.size

        if (original_size <= IMAGE_TARGET_RAW_SIZE and ow <= IMAGE_MAX_WIDTH and oh <= IMAGE_MAX_HEIGHT):
            return {'buffer': image_buffer, 'mediaType': fmt,
                    'dimensions': {'originalWidth': ow, 'originalHeight': oh, 'displayWidth': ow, 'displayHeight': oh}}

        w, h = ow, oh
        needs_dim = w > IMAGE_MAX_WIDTH or h > IMAGE_MAX_HEIGHT

        if not needs_dim and original_size > IMAGE_TARGET_RAW_SIZE:
            if fmt == 'png':
                buf = io.BytesIO()
                img.save(buf, format='PNG', optimize=True)
                if buf.tell() <= IMAGE_TARGET_RAW_SIZE:
                    return {'buffer': buf.getvalue(), 'mediaType': 'png',
                            'dimensions': {'originalWidth': ow, 'originalHeight': oh, 'displayWidth': w, 'displayHeight': h}}
            for q in [80, 60, 40, 20]:
                buf = io.BytesIO()
                img.convert('RGB').save(buf, format='JPEG', quality=q)
                if buf.tell() <= IMAGE_TARGET_RAW_SIZE:
                    return {'buffer': buf.getvalue(), 'mediaType': 'jpeg',
                            'dimensions': {'originalWidth': ow, 'originalHeight': oh, 'displayWidth': w, 'displayHeight': h}}

        if w > IMAGE_MAX_WIDTH:
            h = round(h * IMAGE_MAX_WIDTH / w); w = IMAGE_MAX_WIDTH
        if h > IMAGE_MAX_HEIGHT:
            w = round(w * IMAGE_MAX_HEIGHT / h); h = IMAGE_MAX_HEIGHT

        resized = img.resize((w, h), Image.LANCZOS)
        buf = io.BytesIO()
        save_fmt = fmt.upper() if fmt in ('png', 'jpeg', 'gif', 'webp') else 'JPEG'
        if save_fmt == 'JPEG':
            resized.convert('RGB').save(buf, format='JPEG', quality=85)
        else:
            resized.save(buf, format=save_fmt)
        rb = buf.getvalue()

        if len(rb) > IMAGE_TARGET_RAW_SIZE:
            for q in [80, 60, 40, 20]:
                buf = io.BytesIO()
                resized.convert('RGB').save(buf, format='JPEG', quality=q)
                if buf.tell() <= IMAGE_TARGET_RAW_SIZE:
                    return {'buffer': buf.getvalue(), 'mediaType': 'jpeg',
                            'dimensions': {'originalWidth': ow, 'originalHeight': oh, 'displayWidth': w, 'displayHeight': h}}
            sw = min(w, 1000); sh = round(h * sw / max(w, 1))
            s2 = img.resize((sw, sh), Image.LANCZOS)
            buf = io.BytesIO(); s2.convert('RGB').save(buf, format='JPEG', quality=20)
            return {'buffer': buf.getvalue(), 'mediaType': 'jpeg',
                    'dimensions': {'originalWidth': ow, 'originalHeight': oh, 'displayWidth': sw, 'displayHeight': sh}}

        return {'buffer': rb, 'mediaType': fmt,
                'dimensions': {'originalWidth': ow, 'originalHeight': oh, 'displayWidth': w, 'displayHeight': h}}
    except ImageResizeError:
        raise
    except Exception as error:
        detected = detectImageFormatFromBuffer(image_buffer)
        norm_ext = detected[6:]
        b64_size = (original_size * 4 + 2) // 3
        over_dim = False
        if len(image_buffer) >= 24 and image_buffer[:4] == b'\x89PNG':
            pw = struct.unpack_from('>I', image_buffer, 16)[0]
            ph = struct.unpack_from('>I', image_buffer, 20)[0]
            over_dim = pw > IMAGE_MAX_WIDTH or ph > IMAGE_MAX_HEIGHT
        if b64_size <= API_IMAGE_MAX_BASE64_SIZE and not over_dim:
            return {'buffer': image_buffer, 'mediaType': norm_ext}
        raise ImageResizeError(
            f'Unable to resize image — dimensions exceed the {IMAGE_MAX_WIDTH}x{IMAGE_MAX_HEIGHT}px limit.'
            if over_dim else
            f'Unable to resize image ({_format_file_size(original_size)} raw). Compression failed.'
        )


async def maybeResizeAndDownsampleImageBuffer(image_buffer: bytes, original_size: int, ext: str) -> ResizeResult:
    """Resize image buffer to meet size and dimension constraints."""
    if len(image_buffer) == 0:
        raise ImageResizeError('Image file is empty (0 bytes)')
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _resize_sync, image_buffer, original_size, ext)


async def maybeResizeAndDownsampleImageBlock(image_block: Dict[str, Any]) -> ImageBlockWithDimensions:
    """Resizes an image content block if needed."""
    if image_block.get('source', {}).get('type') != 'base64':
        return {'block': image_block}
    src = image_block['source']
    buf = base64.b64decode(src['data'])
    mt = src.get('media_type', 'image/png')
    ext = mt.split('/')[1] if '/' in mt else 'png'
    resized = await maybeResizeAndDownsampleImageBuffer(buf, len(buf), ext)
    return {
        'block': {'type': 'image', 'source': {'type': 'base64',
            'media_type': f'image/{resized["mediaType"]}',
            'data': base64.b64encode(resized['buffer']).decode()}},
        'dimensions': resized.get('dimensions'),
    }


def _compress_sync(image_buffer: bytes, max_bytes: int, original_media_type: Optional[str]) -> CompressedImageResult:
    fb = (original_media_type or 'image/jpeg').split('/')[1]
    if fb == 'jpg': fb = 'jpeg'
    orig = len(image_buffer)
    if orig <= max_bytes:
        return {'base64': base64.b64encode(image_buffer).decode(),
                'mediaType': detectImageFormatFromBuffer(image_buffer), 'originalSize': orig}
    try:
        Image = _get_pil()
        img = Image.open(io.BytesIO(image_buffer))
        fmt = (img.format or fb).lower()
        if fmt == 'jpg': fmt = 'jpeg'
        for scale in [1.0, 0.75, 0.5, 0.25]:
            w = round((img.width or 2000) * scale); h = round((img.height or 2000) * scale)
            r = img.resize((w, h), Image.LANCZOS) if scale < 1.0 else img
            buf = io.BytesIO()
            if fmt == 'png': r.save(buf, format='PNG', optimize=True)
            elif fmt == 'webp': r.save(buf, format='WEBP', quality=80)
            else: r.convert('RGB').save(buf, format='JPEG', quality=80); fmt = 'jpeg'
            if buf.tell() <= max_bytes:
                return {'base64': base64.b64encode(buf.getvalue()).decode(),
                        'mediaType': f'image/{fmt}', 'originalSize': orig}
        small = img.resize((400, 400), Image.LANCZOS)
        buf = io.BytesIO(); small.convert('RGB').save(buf, format='JPEG', quality=20)
        return {'base64': base64.b64encode(buf.getvalue()).decode(), 'mediaType': 'image/jpeg', 'originalSize': orig}
    except Exception:
        if len(image_buffer) <= max_bytes:
            return {'base64': base64.b64encode(image_buffer).decode(),
                    'mediaType': detectImageFormatFromBuffer(image_buffer), 'originalSize': orig}
        raise ImageResizeError(f'Unable to compress image ({_format_file_size(len(image_buffer))}). Please use a smaller image.')


async def compressImageBuffer(image_buffer: bytes, max_bytes: int = IMAGE_TARGET_RAW_SIZE,
                              original_media_type: Optional[str] = None) -> CompressedImageResult:
    """Compresses an image buffer to fit within a maximum byte size."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _compress_sync, image_buffer, max_bytes, original_media_type)


async def compressImageBufferWithTokenLimit(image_buffer: bytes, max_tokens: int,
                                            original_media_type: Optional[str] = None) -> CompressedImageResult:
    """Compresses an image buffer to fit within a token limit."""
    max_bytes = int(int(max_tokens / 0.125) * 0.75)
    return await compressImageBuffer(image_buffer, max_bytes, original_media_type)


async def compressImageBlock(image_block: Dict[str, Any], max_bytes: int = IMAGE_TARGET_RAW_SIZE) -> Dict[str, Any]:
    """Compresses an image block to fit within a maximum byte size."""
    if image_block.get('source', {}).get('type') != 'base64':
        return image_block
    buf = base64.b64decode(image_block['source']['data'])
    if len(buf) <= max_bytes:
        return image_block
    compressed = await compressImageBuffer(buf, max_bytes)
    return {'type': 'image', 'source': {'type': 'base64', 'media_type': compressed['mediaType'], 'data': compressed['base64']}}


def detectImageFormatFromBuffer(buffer: bytes) -> ImageMediaType:
    """Detect image format from a buffer using magic bytes."""
    if len(buffer) < 4:
        return 'image/png'
    if buffer[:4] == b'\x89PNG':
        return 'image/png'
    if buffer[0] == 0xFF and buffer[1] == 0xD8 and buffer[2] == 0xFF:
        return 'image/jpeg'
    if buffer[:3] == b'GIF':
        return 'image/gif'
    if buffer[:4] == b'RIFF' and len(buffer) >= 12 and buffer[8:12] == b'WEBP':
        return 'image/webp'
    return 'image/png'


def detectImageFormatFromBase64(base64_data: str) -> ImageMediaType:
    """Detect image format from base64 data."""
    try:
        return detectImageFormatFromBuffer(base64.b64decode(base64_data))
    except Exception:
        return 'image/png'


def createImageMetadataText(dims: ImageDimensions, source_path: Optional[str] = None) -> Optional[str]:
    """Creates a text description of image metadata."""
    ow = dims.get('originalWidth'); oh = dims.get('originalHeight')
    dw = dims.get('displayWidth'); dh = dims.get('displayHeight')
    if not (ow and oh and dw and dh and dw > 0 and dh > 0):
        return f'[Image source: {source_path}]' if source_path else None
    was_resized = ow != dw or oh != dh
    if not was_resized and not source_path:
        return None
    parts = []
    if source_path:
        parts.append(f'source: {source_path}')
    if was_resized:
        scale = ow / dw
        parts.append(f'original {ow}x{oh}, displayed at {dw}x{dh}. Multiply coordinates by {scale:.2f} to map to original image.')
    return f'[Image: {", ".join(parts)}]'
