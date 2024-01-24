from collections.abc import Sequence

import torch
from numpy.typing import NDArray
from transformers import AutoModelForSequenceClassification

from bocoel.models.lms.huggingface.causal import Device

from .causal import HuggingfaceCausalLM


class HuggingfaceClassifierLM(HuggingfaceCausalLM):
    def __init__(
        self, model_path: str, batch_size: int, device: Device, choices: int = 2
    ) -> None:
        super().__init__(model_path, batch_size, device)
        self._cls = AutoModelForSequenceClassification.from_pretrained(model_path)
        self._choices = choices

    @torch.no_grad()
    def _classify(self, prompts: Sequence[str], /, choices: int) -> NDArray:
        if choices != self._choices:
            raise ValueError(f"choices must be {self._choices}. Got {choices}.")

        tokenized = self._tokenize(prompts)
        output = self._cls(**tokenized)

        return output.cpu().numpy()