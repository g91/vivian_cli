"""Port of src/utils/processUserInput/processUserInput.ts."""
from __future__ import annotations

from typing import Any, Dict

from ...commands import getCommands, isBridgeSafeCommand
from ...types.textInputTypes import isValidImagePaste
from ..imageStore import storeImages
from ..processUserInput.processBashCommand import processBashCommand
from ..processUserInput.processSlashCommand import processSlashCommand
from ..processUserInput.processTextPrompt import processTextPrompt
from ..queryProfiler import queryCheckpoint
from ..ultraplan.keyword import hasUltraplanKeyword


ProcessUserInputContext = Any
ProcessUserInputBaseResult = Dict[str, Any]
MAX_HOOK_OUTPUT_LENGTH = 10000


async def processUserInput(
    *,
    input,
    preExpansionInput=None,
    mode,
    setToolJSX,
    context,
    pastedContents=None,
    ideSelection=None,
    messages=None,
    setUserInputOnProcessing=None,
    uuid=None,
    isAlreadyProcessing=None,
    querySource=None,
    canUseTool=None,
    skipSlashCommands=None,
    bridgeOrigin=None,
    isMeta=None,
    skipAttachments=None,
):
    del ideSelection, messages, querySource, skipAttachments
    input_string = input if isinstance(input, str) else None
    if mode == "prompt" and input_string is not None and not isMeta:
        if callable(setUserInputOnProcessing):
            setUserInputOnProcessing(input_string)

    queryCheckpoint("query_process_user_input_base_start")
    app_state = context.getAppState() if hasattr(context, "getAppState") else {}
    permission_mode = ((app_state or {}).get("toolPermissionContext") or {}).get("mode")
    result = await processUserInputBase(
        input,
        mode,
        setToolJSX,
        context,
        pastedContents,
        ideSelection,
        messages,
        uuid,
        isAlreadyProcessing,
        querySource,
        canUseTool,
        permission_mode,
        skipSlashCommands,
        bridgeOrigin,
        isMeta,
        skipAttachments,
        preExpansionInput,
    )
    queryCheckpoint("query_process_user_input_base_end")
    return result


def applyTruncation(content):
    if len(content) > MAX_HOOK_OUTPUT_LENGTH:
        return f"{content[:MAX_HOOK_OUTPUT_LENGTH]}... [output truncated - exceeded {MAX_HOOK_OUTPUT_LENGTH} characters]"
    return content


async def processUserInputBase(input, mode, setToolJSX, context, pastedContents=None, ideSelection=None, messages=None, uuid=None, isAlreadyProcessing=None, querySource=None, canUseTool=None, permissionMode=None, skipSlashCommands=None, bridgeOrigin=None, isMeta=None, skipAttachments=None, preExpansionInput=None):
    del ideSelection, messages, querySource, permissionMode, skipAttachments
    input_string = input if isinstance(input, str) else None
    preceding_input_blocks = []
    normalized_input = input
    image_metadata_texts = []

    if isinstance(input, list) and input:
        normalized_input = input
        last_block = input[-1]
        if isinstance(last_block, dict) and last_block.get("type") == "text":
            input_string = last_block.get("text", "")
            preceding_input_blocks = input[:-1]
        else:
            input_string = ""
            preceding_input_blocks = input

    image_contents = [content for content in (pastedContents or {}).values() if isValidImagePaste(content)]
    image_paste_ids = [content.get("id") for content in image_contents if isinstance(content, dict) and content.get("id") is not None]
    if pastedContents:
        try:
            stored = await storeImages(pastedContents)
        except Exception:
            stored = {}
    else:
        stored = {}

    image_content_blocks = []
    for pasted_image in image_contents:
        media_type = pasted_image.get("mediaType") or pasted_image.get("media_type") or "image/png"
        data = pasted_image.get("content") or pasted_image.get("base64") or pasted_image.get("data")
        if not data:
            continue
        image_content_blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": data,
                },
            }
        )
        image_id = pasted_image.get("id")
        stored_path = stored.get(image_id) if isinstance(stored, dict) else None
        if stored_path:
            image_metadata_texts.append(f"Pasted image stored at: {stored_path}")

    effective_skip_slash = bool(skipSlashCommands)
    if bridgeOrigin and input_string is not None and input_string.startswith("/"):
        try:
            body = input_string[1:].split(" ", 1)[0]
            commands = await getCommands(getattr(context, "cwd", None) or __import__("os").getcwd())
            command = next((cmd for cmd in commands if getattr(cmd, "name", "") == body), None)
            if command and isBridgeSafeCommand(command):
                effective_skip_slash = False
        except Exception:
            effective_skip_slash = bool(skipSlashCommands)

    if (
        mode == "prompt"
        and input_string is not None
        and not effective_skip_slash
        and not input_string.startswith("/")
        and hasUltraplanKeyword(preExpansionInput or input_string)
    ):
        input_string = "/ultraplan " + input_string

    attachment_messages = []

    if input_string is not None and mode == "bash":
        return await processBashCommand(input_string, preceding_input_blocks, attachment_messages, context, setToolJSX)

    if input_string is not None and not effective_skip_slash and input_string.startswith("/"):
        return await processSlashCommand(
            input_string,
            preceding_input_blocks,
            image_content_blocks,
            attachment_messages,
            context,
            setToolJSX,
            uuid,
            isAlreadyProcessing,
            canUseTool,
        )

    return addImageMetadataMessage(
        processTextPrompt(
            normalized_input,
            image_content_blocks,
            [int(i) for i in image_paste_ids if i is not None],
            attachment_messages,
            uuid,
            permissionMode,
            isMeta,
        ),
        image_metadata_texts,
    )


def addImageMetadataMessage(result, imageMetadataTexts):
    if imageMetadataTexts:
        messages = list(result.get("messages", []))
        messages.append(
            {
                "type": "system",
                "isMeta": True,
                "text": "\n".join(imageMetadataTexts),
            }
        )
        updated = dict(result)
        updated["messages"] = messages
        return updated
    return result

