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
from typing import Optional, Dict, Any, List, Union

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
    def generate_description(self, image_path: str, prompt: Optional[str] = None) -> Dict[str, Any]:
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
    DEFAULT_PROMPT = "Create a detailed description of this image to help users find it with text search."
    
    def initialize_model(self):
        """Initialize the SmolVLM model and processor."""
        print(f"Initializing SmolVLM model on {self.device}...")
        start_time = time.time()
        
        # Initialize processor and model
        self.processor = AutoProcessor.from_pretrained(
            self.MODEL_NAME,
            cache_dir=self.cache_dir
        )
        
        self.model = AutoModelForVision2Seq.from_pretrained(
            self.MODEL_NAME,
            torch_dtype=torch.bfloat16,
            _attn_implementation="flash_attention_2" if self.device == "cuda" else "eager",
            cache_dir=self.cache_dir
        ).to(self.device)
        
        elapsed = time.time() - start_time
        print(f"SmolVLM model initialized in {elapsed:.2f} seconds")
    
    def generate_description(self, image_path: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a description for the image using SmolVLM.
        
        Args:
            image_path: Path to the image file
            prompt: Custom prompt to use (if None, uses default)
            
        Returns:
            Dictionary containing the description and metadata
        """
        # Verify image exists
        if not os.path.exists(image_path):
            return {"error": f"Image file not found: {image_path}"}
        
        start_time = time.time()
        
        try:
            # Load the image
            image = Image.open(image_path).convert("RGB")
            
            # Prepare the prompt
            text_prompt = prompt or self.DEFAULT_PROMPT
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": text_prompt}
                    ]
                }
            ]
            
            # Apply chat template and prepare model inputs
            prompt = self.processor.apply_chat_template(messages, add_generation_prompt=True)
            inputs = self.processor(text=prompt, images=[image], return_tensors="pt")
            inputs = inputs.to(self.device)
            
            # Generate description
            with torch.no_grad():
                generated_ids = self.model.generate(**inputs, max_new_tokens=500)
            
            generated_text = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
            )[0]
            
            # Extract just the assistant's response
            if "Assistant:" in generated_text:
                description = generated_text.split("Assistant:", 1)[1].strip()
            else:
                description = generated_text.strip()
            
            elapsed = time.time() - start_time
            
            return {
                "description": description,
                "model": self.MODEL_NAME,
                "processing_time": elapsed,
                "prompt": text_prompt
            }
            
        except Exception as e:
            return {
                "error": f"Error generating description: {str(e)}",
                "model": self.MODEL_NAME
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