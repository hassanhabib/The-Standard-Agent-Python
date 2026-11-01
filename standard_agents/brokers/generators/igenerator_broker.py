# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


# The brain, as the framework sees it: a system prompt and a user prompt in, text out. A local
# open-weight model (PyTorch, llama.cpp, anything) is a provider that implements this contract
# and is composed with StandardAgent.use_generator; the framework itself never calls a network.
class IGeneratorBroker(ABC):
    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str: ...
