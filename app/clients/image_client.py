import requests
import json
import logging
import time
import base64
from io import BytesIO
import config

logger = logging.getLogger(__name__)

class ImageClient:
    """
    Client for interacting with Image Generation APIs (Novita, SD WebUI).
    """
    
    def __init__(self):
        self.provider = config.IMAGE_PROVIDER
        self.api_url = config.IMAGE_API_URL
        self.api_key = config.IMAGE_API_KEY
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def generate_image(self, prompt, negative_prompt="", width=1024, height=1024):
        """
        Generates an image based on the configured provider.
        Returns:
            bytes: The image data in bytes, or None if failed.
        """
        if self.provider == "mock":
            return self._generate_mock()
        elif self.provider == "zhipu":
            return self._generate_zhipu(prompt)
        elif self.provider == "novita":
            return self._generate_novita(prompt, negative_prompt, width, height)
        elif self.provider == "sd_webui":
            return self._generate_sd_webui(prompt, negative_prompt, width, height)
        else:
            logger.error(f"Unknown image provider: {self.provider}")
            return None

    def _generate_zhipu(self, prompt):
        """
        Calls Zhipu AI (BigModel) GLM-Image API.
        """
        model = getattr(config, 'IMAGE_MODEL', 'glm-image')
        payload = {
            "model": model,
            "prompt": prompt,
            # glm-image supports various sizes, defaulting to square for avatar/photo consistency
            "size": "1024x1024" 
        }
        
        try:
            logger.info(f"Generating image with Zhipu ({model})...")
            response = requests.post(self.api_url, json=payload, headers=self.headers)
            response.raise_for_status()
            r = response.json()
            
            # Zhipu returns: {"created": ..., "data": [{"url": "..."}]}
            if "data" in r and len(r["data"]) > 0:
                image_url = r["data"][0].get("url")
                if image_url:
                    img_res = requests.get(image_url)
                    return img_res.content
            
            logger.error(f"Zhipu response missing image url: {r}")
            return None
        except Exception as e:
            logger.error(f"Zhipu Generation Failed: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            return None

    def _generate_mock(self):
        """Returns a dummy image for testing."""
        logger.info("Generating mock image...")
        time.sleep(2) # Simulate delay
        # Return the locked image or a placeholder if available, else None
        try:
            with open("locked.png", "rb") as f:
                return f.read()
        except FileNotFoundError:
            return None

    def _generate_sd_webui(self, prompt, negative_prompt, width, height):
        """
        Calls a local Stable Diffusion WebUI API.
        """
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": 20,
            "width": width,
            "height": height,
            "cfg_scale": 7,
            "sampler_name": "Euler a"
        }
        
        try:
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            r = response.json()
            
            # SD WebUI returns base64 string
            if "images" in r and len(r["images"]) > 0:
                image_data = base64.b64decode(r["images"][0])
                return image_data
        except Exception as e:
            logger.error(f"SD WebUI Generation Failed: {e}")
            return None

    def _generate_novita(self, prompt, negative_prompt, width, height):
        """
        Calls Novita AI API (Simplified implementation).
        Note: Novita often uses an Async task model (Submit -> Poll).
        This is a synchronous wrapper for simplicity.
        """
        # 1. Submit Task
        payload = {
            "extra": {
                "response_image_type": "jpeg",
                "enable_nsfw_detection": False
            },
            "request": {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "model_name": "sd_xl_base_1.0.safetensors", # Example model
                "image_num": 1,
                "steps": 30,
                "width": width,
                "height": height,
                "guidance_scale": 7.5
            }
        }
        
        try:
            # Submit
            res = requests.post(self.api_url, json=payload, headers=self.headers)
            res.raise_for_status()
            task_id = res.json().get("task_id")
            
            if not task_id:
                logger.error("Novita: No task_id returned")
                return None
                
            # 2. Poll for result
            for _ in range(30): # Wait up to 60s
                time.sleep(2)
                check_url = f"https://api.novita.ai/v3/async/task-result?task_id={task_id}"
                check_res = requests.get(check_url, headers=self.headers)
                status_data = check_res.json()
                
                if status_data.get("status") == "TASK_STATUS_SUCCEED":
                    images = status_data.get("images", [])
                    if images:
                        image_url = images[0].get("image_url")
                        # Download image
                        img_res = requests.get(image_url)
                        return img_res.content
                elif status_data.get("status") == "TASK_STATUS_FAILED":
                    logger.error("Novita Task Failed")
                    return None
                    
            logger.error("Novita Task Timed Out")
            return None
            
        except Exception as e:
            logger.error(f"Novita Generation Failed: {e}")
            return None
