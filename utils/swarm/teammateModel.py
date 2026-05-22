"""
Port of src/utils/swarm/teammateModel.ts
"""
from __future__ import annotations


# @[MODEL LAUNCH]: Update the fallback model below.
# When the user has never set teammateDefaultModel in /config, new teammates
# use Opus 4.6. Must be provider-aware so Bedrock/Vertex/Foundry customers get
# the correct model ID.
def getHardcodedTeammateModelFallback():
 return vivian_OPUS_4_6_CONFIG[getAPIProvider()]

