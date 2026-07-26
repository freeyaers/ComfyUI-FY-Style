from .nodes import FY_Style
import os
import glob
import tarfile
from pathlib import Path
from aiohttp import web
import nodes

# 插件目录
PLUGIN_DIR = Path(__file__).parent
IMG_DIR = PLUGIN_DIR / "img"

def auto_extract_tar_gz():
    """初始化时自动检测并解压 img/ 目录下的 tar.gz 安装包"""
    if not IMG_DIR.exists():
        return

    # 查找所有 tar.gz 分卷文件
    pattern1 = str(IMG_DIR / "*.tar.gz")
    pattern2 = str(IMG_DIR / "*.tar.gz.*")
    tar_files = sorted(glob.glob(pattern1) + glob.glob(pattern2))

    if not tar_files:
        return

    print(f"[FY-Style] 检测到 {len(tar_files)} 个 tar.gz 安装包，开始自动解压...")

    success_count = 0
    for tar_file in tar_files:
        try:
            with tarfile.open(tar_file, "r:gz") as tar:
                tar.extractall(path=IMG_DIR, filter='data')
            success_count += 1
            print(f"[FY-Style] 已解压: {os.path.basename(tar_file)}")
        except Exception as e:
            print(f"[FY-Style] 解压失败 {os.path.basename(tar_file)}: {e}")

    # 删除所有 tar.gz 安装包
    for tar_file in tar_files:
        try:
            os.remove(tar_file)
        except Exception as e:
            print(f"[FY-Style] 删除失败 {os.path.basename(tar_file)}: {e}")

    print(f"[FY-Style] 解压完成，成功 {success_count}/{len(tar_files)}，已清理安装包")

auto_extract_tar_gz()

NODE_CLASS_MAPPINGS = {
    "FY_Style": FY_Style,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FY_Style": "FY Style",
}

EXTENSION_NAME = "ComfyUI-FY-Style"

# 注册 JS 目录，让 ComfyUI 加载自定义 UI
js_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "js")
nodes.EXTENSION_WEB_DIRS["ComfyUI-FY-Style"] = js_dir

# 注册路由服务 index.html 和相关资源
from server import PromptServer

routes = PromptServer.instance.routes
FY_STYLE_DIR = Path(__file__).parent

# 服务 index.html
@routes.get('/fy-style')
async def serve_fy_style_index(request):
    index_path = FY_STYLE_DIR / 'index.html'
    if index_path.exists():
        return web.FileResponse(index_path)
    else:
        return web.Response(text="FY Style UI not found", status=404)

# 服务 img 目录
@routes.get('/fy-style/img/{path:.*}')
async def serve_fy_style_images(request):
    path = request.match_info.get('path', '')
    if '..' in path or path.startswith('/'):
        return web.Response(text="Invalid path", status=400)
    
    image_path = FY_STYLE_DIR / 'img' / path
    if image_path.exists() and image_path.is_file():
        return web.FileResponse(image_path)
    return web.Response(text="File not found", status=404)

# 服务其他静态资源
@routes.get('/fy-style/{path:.*}')
async def serve_fy_style_static(request):
    path = request.match_info.get('path', '')
    if '..' in path or path.startswith('/'):
        return web.Response(text="Invalid path", status=400)
    
    static_path = FY_STYLE_DIR / path
    if static_path.exists() and static_path.is_file():
        return web.FileResponse(static_path)
    return web.Response(text="File not found", status=404)

# API: 获取当前选中的图片信息（供 iframe 轮询 fallback 使用）
@routes.get('/fy-style/selected-image')
async def get_selected_image(request):
    return web.json_response({"filename": "", "value": ""})