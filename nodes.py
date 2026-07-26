# Hack: string type that is always equal in not equal comparisons
class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False


# Our any instance wants to be a wildcard string
ANY = AnyType("*")

import torch
import numpy as np
from PIL import Image
from pathlib import Path

# 获取插件目录
PLUGIN_DIR = Path(__file__).parent

class FY_Style:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "optional": {
                "positive_prompt": (ANY, {"default": ""}),
                "negative_prompt": (ANY, {"default": ""}),
                "selected_image": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "IMAGE")
    RETURN_NAMES = ("positive_prompt", "negative_prompt", "image")
    FUNCTION = "main"
    CATEGORY = "FY Style"
    DESCRIPTION = "FY Style - Pass through prompt data with image output"

    def main(self, positive_prompt="", negative_prompt="", selected_image=""):
        # 解析 widget 值：格式 filename|prompt|negative_prompt
        parts = (selected_image or '').split('|')
        image_filename = parts[0] if len(parts) > 0 else ""
        image_positive = parts[1] if len(parts) > 1 else ""
        image_negative = parts[2] if len(parts) > 2 else ""

        # 组合提示词：图片提示词在前，用户输入在后，用逗号分隔
        if positive_prompt:
            combined_positive = f"{image_positive}, {positive_prompt}" if image_positive else positive_prompt
        else:
            combined_positive = image_positive

        if negative_prompt:
            combined_negative = f"{image_negative}, {negative_prompt}" if image_negative else negative_prompt
        else:
            combined_negative = image_negative

        result = (combined_positive, combined_negative)

        # 验证选中的图片
        if not image_filename:
            raise ValueError("FY_Style: 请在 FY Style 面板中选择一张图片")

        img_path = PLUGIN_DIR / "img" / image_filename

        if not img_path.exists() or not img_path.is_file():
            raise ValueError(f"FY_Style: 图片文件不存在: {img_path}")

        # 加载图片
        try:
            img = Image.open(img_path).convert("RGB")
            img = torch.from_numpy(np.array(img)).float() / 255.0
            img = img.unsqueeze(0)
            return result + (img,)
        except Exception as e:
            raise ValueError(f"FY_Style: 图片加载失败: {e}")
