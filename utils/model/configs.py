"""Port of src/utils/model/configs.ts"""
from __future__ import annotations

from typing import Dict, Literal

APIProvider = Literal['firstParty', 'bedrock', 'vertex', 'foundry']
ModelName = str
ModelConfig = Dict[str, str]  # APIProvider -> ModelName

vivian_3_7_SONNET_CONFIG: ModelConfig = {
    'firstParty': 'vivian-3-7-sonnet-20250219',
    'bedrock': 'us.anthropic.vivian-3-7-sonnet-20250219-v1:0',
    'vertex': 'vivian-3-7-sonnet@20250219',
    'foundry': 'vivian-3-7-sonnet',
}

vivian_3_5_V2_SONNET_CONFIG: ModelConfig = {
    'firstParty': 'vivian-3-5-sonnet-20241022',
    'bedrock': 'anthropic.vivian-3-5-sonnet-20241022-v2:0',
    'vertex': 'vivian-3-5-sonnet-v2@20241022',
    'foundry': 'vivian-3-5-sonnet',
}

vivian_3_5_HAIKU_CONFIG: ModelConfig = {
    'firstParty': 'vivian-3-5-haiku-20241022',
    'bedrock': 'us.anthropic.vivian-3-5-haiku-20241022-v1:0',
    'vertex': 'vivian-3-5-haiku@20241022',
    'foundry': 'vivian-3-5-haiku',
}

vivian_HAIKU_4_5_CONFIG: ModelConfig = {
    'firstParty': 'vivian-haiku-4-5-20251001',
    'bedrock': 'us.anthropic.vivian-haiku-4-5-20251001-v1:0',
    'vertex': 'vivian-haiku-4-5@20251001',
    'foundry': 'vivian-haiku-4-5',
}

vivian_SONNET_4_CONFIG: ModelConfig = {
    'firstParty': 'vivian-sonnet-4-20250514',
    'bedrock': 'us.anthropic.vivian-sonnet-4-20250514-v1:0',
    'vertex': 'vivian-sonnet-4@20250514',
    'foundry': 'vivian-sonnet-4',
}

vivian_SONNET_4_5_CONFIG: ModelConfig = {
    'firstParty': 'vivian-sonnet-4-5-20250929',
    'bedrock': 'us.anthropic.vivian-sonnet-4-5-20250929-v1:0',
    'vertex': 'vivian-sonnet-4-5@20250929',
    'foundry': 'vivian-sonnet-4-5',
}

vivian_OPUS_4_CONFIG: ModelConfig = {
    'firstParty': 'vivian-opus-4-20250514',
    'bedrock': 'us.anthropic.vivian-opus-4-20250514-v1:0',
    'vertex': 'vivian-opus-4@20250514',
    'foundry': 'vivian-opus-4',
}

vivian_OPUS_4_1_CONFIG: ModelConfig = {
    'firstParty': 'vivian-opus-4-1-20250805',
    'bedrock': 'us.anthropic.vivian-opus-4-1-20250805-v1:0',
    'vertex': 'vivian-opus-4-1@20250805',
    'foundry': 'vivian-opus-4-1',
}

vivian_OPUS_4_5_CONFIG: ModelConfig = {
    'firstParty': 'vivian-opus-4-5-20251101',
    'bedrock': 'us.anthropic.vivian-opus-4-5-20251101-v1:0',
    'vertex': 'vivian-opus-4-5@20251101',
    'foundry': 'vivian-opus-4-5',
}

vivian_OPUS_4_6_CONFIG: ModelConfig = {
    'firstParty': 'vivian-opus-4-6',
    'bedrock': 'us.anthropic.vivian-opus-4-6-v1',
    'vertex': 'vivian-opus-4-6',
    'foundry': 'vivian-opus-4-6',
}

vivian_SONNET_4_6_CONFIG: ModelConfig = {
    'firstParty': 'vivian-sonnet-4-6',
    'bedrock': 'us.anthropic.vivian-sonnet-4-6',
    'vertex': 'vivian-sonnet-4-6',
    'foundry': 'vivian-sonnet-4-6',
}

ALL_MODEL_CONFIGS: Dict[str, ModelConfig] = {
    'haiku35': vivian_3_5_HAIKU_CONFIG,
    'haiku45': vivian_HAIKU_4_5_CONFIG,
    'sonnet35': vivian_3_5_V2_SONNET_CONFIG,
    'sonnet37': vivian_3_7_SONNET_CONFIG,
    'sonnet40': vivian_SONNET_4_CONFIG,
    'sonnet45': vivian_SONNET_4_5_CONFIG,
    'sonnet46': vivian_SONNET_4_6_CONFIG,
    'opus40': vivian_OPUS_4_CONFIG,
    'opus41': vivian_OPUS_4_1_CONFIG,
    'opus45': vivian_OPUS_4_5_CONFIG,
    'opus46': vivian_OPUS_4_6_CONFIG,
}

ModelKey = str  # keyof ALL_MODEL_CONFIGS

# Runtime list of canonical model IDs
CANONICAL_MODEL_IDS = [cfg['firstParty'] for cfg in ALL_MODEL_CONFIGS.values()]

# Map canonical ID -> internal short key
CANONICAL_ID_TO_KEY: Dict[str, str] = {
    cfg['firstParty']: key for key, cfg in ALL_MODEL_CONFIGS.items()
}
