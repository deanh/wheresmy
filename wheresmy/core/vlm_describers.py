"""
VLM Describers - Image description generators using vision-language models.

This module provides a collection of classes for generating textual descriptions of
images using various vision-language models (VLMs). The design is modular, allowing
easy swapping of different VLM implementations.

Available describers:
- SmolVLMDescriber: Uses the SmolVLM-Instruct model for image description
"""

import os
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForVision2Seq


class BaseVLMDescriber(ABC):
    """Abstract base class for all VLM-based image describers."""

    def __init__(self, device: Optional[str] = None, cache_dir: Optional[str] = None):
        """
        Initialize the VLM describer.

        Args:
            device: Device to run inference on ('cuda', 'cpu', etc.). If None, will auto-detect.
            cache_dir: Directory to cache downloaded models. If None, uses default.
        """
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.cache_dir = cache_dir

        # Set to True once the model is loaded
        self._is_initialized = False

    def ensure_initialized(self):
        """Ensure the model is initialized before use."""
        if not self._is_initialized:
            self.initialize_model()
            self._is_initialized = True

    @abstractmethod
    def initialize_model(self):
        """Initialize the model and processor. To be implemented by subclasses."""
        pass

    @abstractmethod
    def generate_description(
        self, image_path: str, prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a description for the image.

        Args:
            image_path: Path to the image file
            prompt: Optional custom prompt to use

        Returns:
            Dictionary containing the description and metadata
        """
        pass

    def __call__(self, image_path: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a description when the object is called directly.

        Args:
            image_path: Path to the image file
            prompt: Optional custom prompt to use

        Returns:
            Dictionary containing the description and metadata
        """
        self.ensure_initialized()
        return self.generate_description(image_path, prompt)


class SmolVLMDescriber(BaseVLMDescriber):
    """Image describer using the SmolVLM-Instruct model."""

    MODEL_NAME = "HuggingFaceTB/SmolVLM-Instruct"
    DEFAULT_PROMPT = (
        "Create a detailed description of this image to help"
        "users find it with text search."
    )

    def initialize_model(self):
        """Initialize the SmolVLM model and processor."""
        import logging

        logger = logging.getLogger(__name__)

        logger.info(f"Initializing SmolVLM model on {self.device}...")
        start_time = time.time()

        try:
            # Initialize processor
            logger.info("Loading processor...")
            processor_start = time.time()
            self.processor = AutoProcessor.from_pretrained(
                self.MODEL_NAME, cache_dir=self.cache_dir
            )
            logger.info(
                f"Processor loaded in {time.time() - processor_start:.2f} seconds"
            )

            # Initialize model
            logger.info("Loading model...")
            model_start = time.time()
            self.model = AutoModelForVision2Seq.from_pretrained(
                self.MODEL_NAME,
                torch_dtype=torch.bfloat16,
                _attn_implementation=(
                    "flash_attention_2" if self.device == "cuda" else "eager"
                ),
                cache_dir=self.cache_dir,
            )
            logger.info(f"Model loaded in {time.time() - model_start:.2f} seconds")

            # Move model to device
            logger.info(f"Moving model to {self.device}...")
            device_start = time.time()
            self.model = self.model.to(self.device)
            logger.info(
                f"Model moved to {self.device} in {time.time() - device_start:.2f} seconds"
            )

            elapsed = time.time() - start_time
            logger.info(f"SmolVLM model fully initialized in {elapsed:.2f} seconds")

        except Exception as e:
            logger.error(f"Error initializing SmolVLM model: {str(e)}")
            raise

    def generate_description(
        self, image_path: str, prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a description for the image using SmolVLM.

        Args:
            image_path: Path to the image file
            prompt: Custom prompt to use (if None, uses default)

        Returns:
            Dictionary containing the description and metadata
        """
        import logging

        logger = logging.getLogger(__name__)

        logger.info(f"Generating description for image: {image_path}")

        # Verify image exists
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return {"error": f"Image file not found: {image_path}"}

        start_time = time.time()

        try:
            # Load the image
            logger.info("Loading image...")
            image_start = time.time()
            image = Image.open(image_path).convert("RGB")
            logger.info(f"Image loaded in {time.time() - image_start:.2f} seconds")

            # Prepare the prompt
            text_prompt = prompt or self.DEFAULT_PROMPT
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": text_prompt},
                    ],
                }
            ]

            # Apply chat template and prepare model inputs
            logger.info("Preparing inputs...")
            prep_start = time.time()
            prompt = self.processor.apply_chat_template(
                messages, add_generation_prompt=True
            )
            inputs = self.processor(text=prompt, images=[image], return_tensors="pt")
            inputs = inputs.to(self.device)
            logger.info(f"Inputs prepared in {time.time() - prep_start:.2f} seconds")

            # Generate description
            logger.info("Generating text...")
            gen_start = time.time()
            with torch.no_grad():
                generated_ids = self.model.generate(**inputs, max_new_tokens=500)
            logger.info(f"Text generation took {time.time() - gen_start:.2f} seconds")

            # Decode the generated text
            logger.info("Decoding text...")
            decode_start = time.time()
            generated_text = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
            )[0]
            logger.info(f"Text decoded in {time.time() - decode_start:.2f} seconds")

            # Extract just the assistant's response
            if "Assistant:" in generated_text:
                description = generated_text.split("Assistant:", 1)[1].strip()
            else:
                description = generated_text.strip()

            elapsed = time.time() - start_time
            logger.info(f"Description generated in {elapsed:.2f} seconds")

            return {
                "description": description,
                "model": self.MODEL_NAME,
                "processing_time": elapsed,
                "prompt": text_prompt,
            }

        except Exception as e:
            logger.error(f"Error generating description: {str(e)}")
            return {
                "error": f"Error generating description: {str(e)}",
                "model": self.MODEL_NAME,
            }


# Factory function to get the appropriate describer
def get_vlm_describer(model_name: str = "smolvlm", **kwargs) -> BaseVLMDescriber:
    """
    Factory function to create the requested VLM describer.

    Args:
        model_name: Name of the VLM model to use ('smolvlm', etc.)
        **kwargs: Additional arguments to pass to the describer constructor

    Returns:
        An instance of the requested VLM describer

    Raises:
        ValueError: If the requested model is not supported
    """
    model_name = model_name.lower()

    if model_name == "smolvlm":
        return SmolVLMDescriber(**kwargs)
    else:
        raise ValueError(f"Unsupported VLM model: {model_name}")


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python vlm_describers.py <image_path> [model_name]")
        sys.exit(1)

    image_path = sys.argv[1]
    model_name = sys.argv[2] if len(sys.argv) > 2 else "smolvlm"

    describer = get_vlm_describer(model_name)
    result = describer(image_path)

    print(f"Model: {result.get('model')}")
    print(f"Time: {result.get('processing_time', 'N/A'):.2f}s")
    print("Description:")
    print(result.get("description", "Error: " + result.get("error", "Unknown error")))
