import os
import re
import json
from urllib.parse import unquote

# 配置项
IMG_DIR = "img"  # 本地目录
WEB_IMG_DIR = "/fy-style/img"  # Web 访问路径
OUTPUT_FILE = "index.html"
CARDS_PER_ROW = 4  # 每行显示的卡片数量
LANG_DIR = "lang"  # 语言包目录

# 系统默认标签映射表（单 [] 格式）
# 键：标签名（英文），值：(中文名称，英文名称)
DEFAULT_CATEGORY_TAGS = {
    '_3d_rendering': ('3D渲染', '3D Rendering'),
    '_illustration': ('插画', 'illustration'),
    '_movie': ('电影', 'Movie'),
    '_painting': ('绘画', 'Painting'),
    '_painting_style': ('绘画风格','Painting Style'),
    '_photography_style': ('摄影风格', 'Photography Style'),
    '_graphics': ('图形', 'Graphics'),
}

def load_language_packs():
    """ 读取 lang 目录下的所有语言包文件
    返回格式: {
        'zh-cn': { 'base': {...}, 'placeholder': {...}, 'classify': {...} },
        'en': { ... }
    }
    """
    lang_packs = {}
    lang_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), LANG_DIR)
    if not os.path.exists(lang_dir):
        print(f"警告：找不到语言包目录 '{lang_dir}'")
        return lang_packs
    
    for filename in os.listdir(lang_dir):
        if filename.endswith('.json'):
            lang_code = filename[:-5]  # 去掉 .json
            filepath = os.path.join(lang_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lang_packs[lang_code] = json.load(f)
                print(f"已加载语言包: {lang_code}")
            except Exception as e:
                print(f"警告：加载语言包失败 {filename}: {e}")
    return lang_packs


def merge_classify_into_lang(lang_packs, categories):
    """ 从图片分类中提取 classify 数据并合并到语言包中
    categories 格式：{ 'tag': 数量，... }
    为每个语言包添加 classify 数据（tag 作为键，对应语言名称作为值）
    """
    for lang_code, pack in lang_packs.items():
        if 'classify' not in pack:
            pack['classify'] = {}

        # 添加系统默认标签（tag 作为键）
        for tag, (cn, en) in DEFAULT_CATEGORY_TAGS.items():
            pack['classify'][tag] = cn if lang_code == 'zh-cn' else en

        # 为图片中出现的动态分类补充到语言包
        for cat in categories:
            if cat not in pack['classify']:
                pack['classify'][cat] = cat

        # 添加"其它"分类
        pack['classify']['_other'] = '其它' if lang_code == 'zh-cn' else 'Other'


def parse_filename(filename, lang_packs=None):
    """ 解析文件名，提取分类、序号、名称和提示词
    支持格式：
    [_标签]序号-名称(提示词){URL}.ext
    序号-名称(提示词){URL}.ext
    简单文件名如 123.jpg
    lang_packs: 语言包，用于查找分类的显示名称
    """
    # 先提取 URL（从 {} 中提取，最后处理）
    url = ""
    url_match = re.search(r'\{(.*?)\}', filename)
    if url_match:
        url = url_match.group(1)
        try:
            url = unquote(url)
        except Exception:
            pass

    # 移除 URL 部分后再解析其余结构
    name_only = re.sub(r'\{.*?\}', '', filename)

    # 尝试单 [] 格式
    pattern_single = r"\[(.+?)\]\s*(\d+)\s*-\s*(.+?)\s*\((.+?)\)\.[a-zA-Z0-9]+$"
    match_single = re.match(pattern_single, name_only)
    if match_single:
        tag = match_single.group(1)
        index = int(match_single.group(2))
        desc_cn = match_single.group(3)
        raw_prompt = match_single.group(4)
        # 优先从 zh-cn 语言包获取分类显示名，其次 fallback 到 DEFAULT_CATEGORY_TAGS
        category_cn = tag
        zh_pack = lang_packs.get('zh-cn', {}) if lang_packs else {}
        if 'classify' in zh_pack and tag in zh_pack['classify']:
            category_cn = zh_pack['classify'][tag]
        elif tag in DEFAULT_CATEGORY_TAGS:
            category_cn = DEFAULT_CATEGORY_TAGS[tag][0]
    else:
        # 尝试无 [] 格式
        pattern_none = r"(\d+)\s*-\s*(.+?)\s*\((.+?)\)\.[a-zA-Z0-9]+$"
        match_none = re.match(pattern_none, name_only)
        if match_none:
            index = int(match_none.group(1))
            desc_cn = match_none.group(2)
            raw_prompt = match_none.group(3)
            category_cn = "其它"
        else:
            # 简单文件名如 123.jpg
            simple_pattern = r"^(.+?)\.[a-zA-Z0-9]+$"
            simple_match = re.match(simple_pattern, name_only)
            if simple_match:
                name = simple_match.group(1)
                index_match = re.match(r"(\d+)", name)
                if index_match:
                    index = int(index_match.group(1))
                    desc_cn = name[len(index_match.group(1)):].strip()
                else:
                    index = None
                    desc_cn = name
                category_cn = "其它"
                raw_prompt = ""
            else:
                return None
        tag = None

    # 解析括号内的提示词，通过 ---- 分割正向和负向
    positive_prompt = ""
    negative_prompt = ""
    if raw_prompt and "----" in raw_prompt:
        parts = raw_prompt.split("----", 1)
        positive_prompt = parts[0].strip() if len(parts) > 0 else ""
        negative_prompt = parts[1].strip() if len(parts) > 1 else ""
    elif raw_prompt:
        positive_prompt = raw_prompt.strip()
    return {
        "category": category_cn,
        "tag": tag,
        "desc": desc_cn,
        "prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "url": url,
        "filename": filename,
        "index": index
    }

def generate_html(images_data, lang_packs, categories, category_counts):
    # 1. 对图片列表进行排序，确保按序号从小到大排列
    images_data.sort(key=lambda x: x["index"] if x["index"] is not None else 0)
    total_count = len(images_data)
    
    # 将数据转换为 JSON 格式供前端 JS 使用
    images_data_with_en = []
    for img in images_data:
        img_with_en = img.copy()
        img_with_en["desc_en"] = img["desc"]
        images_data_with_en.append(img_with_en)

    json_data = json.dumps(images_data_with_en, ensure_ascii=False)
    json_categories = json.dumps(categories, ensure_ascii=False)
    json_category_counts = json.dumps(category_counts, ensure_ascii=False)
    # tag -> 中文显示名映射，供前端过滤使用
    category_name_map = {tag: next((img["category"] for img in images_data_with_en if img.get("tag") == tag), tag) for tag in categories}
    json_category_name_map = json.dumps(category_name_map, ensure_ascii=False)

    # 构建语言包数据（所有语言）
    lang_packs_json = json.dumps(lang_packs, ensure_ascii=False)

    html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image Tile Gallery</title>
    <style>
        :root {{
            --bg-color: #f4f4f4;
            --card-bg: #ffffff;
            --text-main: #1a1a1a;
            --text-sub: #666666;
            --gray-border: #dcdcdc;
            --gray-bg: #e8e8e8;
        }}
        /* 暗色模式 */
        :root.dark {{
            --bg-color: #1a1a1a;
            --card-bg: #242424;
            --text-main: #e0e0e0;
            --text-sub: #888888;
            --gray-border: #3a3a3a;
            --gray-bg: #323232;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg-color);
            color: var(--text-main);
            padding: 20px;
            transition: background 0.3s ease, color 0.3s ease;
        }}
        /* 主题切换按钮 */
        .theme-toggle {{
            position: fixed;
            top: 5px;
            right: 38px;
            width: 28px;
            height: 28px;
            border: none;
            background: var(--gray-bg);
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            transition: all 0.2s ease;
        }}
        .theme-toggle:hover {{
            transform: scale(1.1);
            background: var(--card-bg);
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        .theme-toggle svg {{
            width: 14px;
            height: 14px;
            fill: var(--text-main);
        }}
        /* 语言切换按钮 */
        .lang-toggle {{
            position: fixed;
            top: 5px;
            right: 5px;
            width: 28px;
            height: 28px;
            border: none;
            background: var(--gray-bg);
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            transition: all 0.2s ease;
            font-size: 10px;
            font-weight: bold;
            color: var(--text-main);
        }}
        .lang-toggle:hover {{
            transform: scale(1.1);
            background: var(--card-bg);
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        /* 顶部固定容器：包含选项卡和搜索栏 */
        .header-container {{
            position: sticky;
            top: 0;
            background: var(--bg-color);
            z-index: 100;
            padding-bottom: 10px;
            margin-bottom: 10px;
            border-bottom: 0px solid var(--gray-border);
        }}
        /* 选项卡样式 */
        .tabs {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 10px;
        }}
        .tab-btn {{
            padding: 4px 12px;
            border: 0px solid var(--gray-border);
            background: var(--gray-bg);
            color: var(--text-sub);
            border-radius: 0;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s ease;
            white-space: nowrap;
        }}
        .tab-btn:hover {{ background: var(--gray-border); color: var(--text-main); }}
        .tab-btn.active {{ background: #888; color: white; border-color: #888; }}
        /* 搜索栏样式 */
        .search-bar {{ display: flex; gap: 8px; }}
        .search-bar input {{
            flex: 1;
            padding: 6px 10px;
            border: 1px solid var(--gray-border);
            box-sizing: border-box;
            border-radius: 0;
            font-size: 13px;
            outline: none;
        }}
        .search-bar button {{
            padding: 6px 15px;
            border: 0px solid var(--gray-border);
            background: var(--gray-bg);
            color: var(--text-sub);
            border-radius: 0;
            cursor: pointer;
            font-size: 13px;
            white-space: nowrap;
        }}
        .search-bar button:hover {{ background: var(--gray-border); color: var(--text-main); }}
        /* 查询结果数量显示 */
        .result-count {{ font-size: 13px; color: var(--text-sub); margin: 10px 0; padding-left: 2px; }}
        /* 网格布局 */
        .grid {{ display: flex; flex-wrap: wrap; gap: 10px; }}
        /* 卡片样式 */
        .card {{
            width: calc(100%/4 - 90/4px);
            min-width: 80px;
            background: var(--card-bg);
            border-radius: 0;
            overflow: hidden;
            border: 0px solid var(--gray-border);
            position: relative;
            transition: border-color 0.2s ease;
            cursor: pointer;
        }}
        .card:hover {{ border-color: var(--text-main); }}
        .card.s {{ border: 2px solid var(--text-main) !important; }}
        /* 选中标记：右上角斜三角 */
        .card-checkmark {{
            position: absolute;
            top: 0;
            right: 0;
            width: 30px;
            height: 30px;
            display: none;
            z-index: 5;
        }}
        .card.s .card-checkmark {{
            display: block;
        }}
        .card-checkmark svg {{
            width: 100%;
            height: 100%;
        }}
        /* 暗模式：白底黑勾 */
        :root.dark .card-checkmark-bg {{ fill: #ffffff; }}
        :root.dark .card-checkmark-icon {{ fill: #000000; }}
        /* 亮模式：黑底白勾 */
        :root:not(.dark) .card-checkmark-bg {{ fill: #000000; }}
        :root:not(.dark) .card-checkmark-icon {{ fill: #ffffff; }}
        /* 序号标签：默认隐藏，悬停显示 */
        .index-tag {{
            position: absolute;
            bottom: 35px;
            right: 0;
            background: rgb(100 100 100 / 33%);
            color: white;
            font-size: 12px;
            padding: 0px 5px;
            z-index: 2;
            white-space: nowrap;
            display: none;
        }}
        .card:hover .index-tag {{ display: block; }}
        /* 放大镜图标 */
        .zoom-icon {{
            position: absolute;
            top: 5px;
            left: 5px;
            width: 24px;
            height: 24px;
            background-color: rgba(255, 255, 255, 0.9);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 3;
            opacity: 0;
            transition: opacity 0.2s ease, transform 0.1s;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }}
        .card:hover .zoom-icon {{ opacity: 1; }}
        .zoom-icon:active {{ transform: scale(0.9); }}
        .zoom-icon svg {{ width: 14px; height: 14px; fill: #333; }}
        /* 图片容器 */
        .img-wrapper {{
            width: 100%;
            aspect-ratio: 1 / 1;
            overflow: hidden;
            background: #eee;
        }}
        .img-wrapper img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }}
        /* 文本信息区 */
        .info {{ padding: 8px 10px; pointer-events: none; }} /* pointer-events: none 防止文本干扰卡片点击 */
        .info-title {{
            font-size: 13px;
            font-weight: 600;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-bottom: 2px;
        }}
        .info-prompt {{
            font-size: 11px;
            color: var(--text-sub);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .info-prompt-negative {{
            display: none; /* 默认隐藏 */
        }}
        /* 无内容提示 */
        .no-result {{
            width: 100%;
            text-align: center;
            color: #999;
            padding: 60px 0;
            font-size: 14px;
        }}
        /* 放大预览模态框 */
        .modal {{
            display: none;
            position: fixed;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.9);
            padding: 20px;
        }}
        .modal-content {{
            position: relative;
            max-width: 90%;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .modal-content img {{
            max-width: 100%;
            max-height: 70vh; /* 限制图片最大高度，为下方文字留出空间 */
            object-fit: contain; /* 确保图片完整显示 */
            border-radius: 2px;
            box-shadow: 0 0 20px rgba(0,0,0,0.5);
            margin-bottom: 20px; /* 图片和文字之间的间距 */
        }}
        .close-modal {{
            position: absolute;
            top: -10px;
            right: -45px;
            color: #fff;
            font-size: 35px;
            font-weight: bold;
            cursor: pointer;
            background: none;
            border: none;
            padding: 0 10px;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }}
        .close-modal:hover {{ color: #bbb; }}
        /* 模态框中的文字信息 */
        .modal-info {{
            color: #fff;
            text-align: center;
            width: 100%;
            max-width: 800px; /* 限制文字区域的最大宽度 */
        }}
        .modal-title {{
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 10px;
            word-break: break-all;
        }}
        #modalUrlLinkWrapper {{
            display: inline-block;
            margin-left: 8px;
            vertical-align: middle;
            text-decoration: none;
            background-color: rgb(255 255 255 / 20%);
            border-radius: 30px;
            width: 25px;
            height: 25px;
            line-height: 30px;
        }}
        #modalUrlLinkWrapper svg {{
            width: 18px;
            height: 22px;
        }}
        .modal-prompt {{
            font-size: 0.9em;
            color: #ccc;
            line-height: 1.5;
            word-break: break-all;
        }}
        .modal-prompt-negative {{
            font-size: 0.9em;
            color: #ff4b00;
            word-break: break-all;
        }}
        .modal-prompt-wrapper {{
            display: flex;
            align-items: flex-start;
            gap: 5px;
            align-items: center;
            justify-content: center;
            margin-bottom: 5px;
        }}
        .copy-icon {{
            flex-shrink: 0;
            cursor: pointer;
            opacity: 0.6;
            transition: opacity 0.2s;
            margin-top: 2px;
        }}
        .copy-icon:hover {{
            opacity: 1;
        }}
        .copy-icon svg {{
            fill: currentColor;
        }}
        /* 新增：底部居中提示条样式 */
        .selection-tip {{
            position: fixed;
            justify-content: center;
            align-items: center;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: rgba(0, 0, 0, 0.85);
            color: #fff;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 14px;
            display: none; /* 默认隐藏 */
            z-index: 999;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        /* 暗色模式下提示条样式 */
        .selection-tip.dark {{
            background-color: #ffffff;
            color: #000000;
            box-shadow: 0 2px 8px rgba(0,0,0,0.5);
        }}
        .selection-tip .locate-icon {{
            cursor: pointer;
            opacity: 0.8;
            transition: opacity 0.2s;
        }}
        .selection-tip .locate-icon:hover {{
            opacity: 1;
        }}
        /* columnsSelect 下拉框样式 */
        #columnsSelect {{
            width: 100px;
            padding: 6px 10px;
            border: 1px solid var(--gray-border);
            border-radius: 0;
            font-size: 13px;
            outline: none;
            background: var(--card-bg);
            color: var(--text-main);
        }}
        /* 禁止选择和拖拽所有图片 */
        body {{
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
            user-select: none;
        }}
        img {{
            -webkit-user-drag: none;
            pointer-events: none;
        }}
        .img-wrapper {{
            pointer-events: auto;
        }}
        .zoom-icon {{
            pointer-events: auto;
        }}
    </style>
</head>
    <body>
        <!-- 语言切换按钮 -->
        <button id="langToggle" class="lang-toggle" onclick="toggleLang()" title="切换语言">CN</button>
        <!-- 主题切换按钮 -->
        <button id="themeToggle" class="theme-toggle" onclick="toggleTheme()" title="切换主题">
            <svg id="themeIcon" viewBox="0 0 24 24"><path d="M20 8.69V4h-4.69L12 .69 8.69 4H4v4.69L.69 12 4 15.31V20h4.69L12 23.31 15.31 20H20v-4.69L23.31 12 20 8.69zM12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6 6 2.69 6 6-2.69 6-6 6zm0-10c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4z"/></svg>
        </button>
        <div class="header-container">
            <div class="tabs" id="tabsContainer"></div>
            <div class="search-bar" style="display: flex; align-items: center; gap: 8px;">
                <select id="columnsSelect" onchange="changeColumns(this.value)">
                    <option value="1">1 columns</option>
                    <option value="2">2 columns</option>
                    <option value="3">3 columns</option>
                    <option value="4" selected>4 columns</option>
                    <option value="5">5 columns</option>
                    <option value="6">6 columns</option>
                    <option value="7">7 columns</option>
                    <option value="8">8 columns</option>
                    <option value="9">9 columns</option>
                    <option value="10">10 columns</option>
                </select>
                <input type="text" id="searchInput" placeholder="输入关键字搜索描述或提示词..." data-i18n-placeholder="search">
                <button onclick="handleSearch()" data-i18n="search">查询</button>
                <button onclick="handleReset()" data-i18n="reset">重置</button>
                <button onclick="openInNewWindow()" title="在新窗口中打开" data-i18n="new_window">新窗口</button>
            </div>
        </div>
    <div class="result-count" id="resultCount"></div>
    <div class="grid" id="gridContainer"></div>
    
    <!-- 新增：底部居中提示条 -->
    <div id="selectionTip" class="selection-tip">
        <span id="tipText"></span>
        <span id="locateIcon" class="locate-icon" title="定位到选中项">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>
        </span>
    </div>

    <!-- 放大预览模态框 -->
    <div id="imageModal" class="modal">
        <div class="modal-content">
            <button class="close-modal" onclick="closeModal()">&times;</button>
            <img id="modalImage" src="" alt="">
            <div class="modal-info">
                <div id="modalTitle" class="modal-title"></div>

            </div>
        </div>
    </div>

    <script>
        const images = {json_data};
        const categories = {json_categories};
        const categoryCounts = {json_category_counts};
        const totalImages = {total_count};
        const langPacks = {lang_packs_json};
        const categoryNameMap = {json_category_name_map};

        const tabsContainer = document.getElementById('tabsContainer');
        const gridContainer = document.getElementById('gridContainer');
        const searchInput = document.getElementById('searchInput');
        const resultCountDiv = document.getElementById('resultCount');
        const imageModal = document.getElementById('imageModal');
        const modalImage = document.getElementById('modalImage');
        const modalTitle = document.getElementById('modalTitle');
        // 新增：获取提示条相关元素
        const selectionTip = document.getElementById('selectionTip');
        const tipText = document.getElementById('tipText');
        const locateIcon = document.getElementById('locateIcon');
        const langToggle = document.getElementById('langToggle');
        const columnsSelect = document.getElementById('columnsSelect');

        let currentCategory = '全部';
        let currentTag = null;
        let selectedCardData = null; // 用于存储当前选中卡片的数据
        let currentColumns = 4; // 默认4列

        // 当前语言
        let currentLang = 'cn';
        // 当前语言包数据
        let currentLangPack = langPacks['cn'];

        // 获取语言显示名称（zh-cn -> CN, en -> EN）
        function getLangDisplay(langCode) {{
            const parts = langCode.split('-');
            return parts[parts.length - 1].toUpperCase();
        }}

        // 切换语言
        function toggleLang() {{
            const langCodes = Object.keys(langPacks);
            const currentIndex = langCodes.indexOf(currentLang);
            const nextIndex = (currentIndex + 1) % langCodes.length;
            currentLang = langCodes[nextIndex];
            currentLangPack = langPacks[currentLang];
            langToggle.textContent = getLangDisplay(currentLang);
            langToggle.style.fontWeight = currentLang === 'cn' ? 'bold' : 'normal';
            saveLang(currentLang);
            applyLang();
        }}

        // 保存语言偏好
        function saveLang(lang) {{
            document.cookie = 'fy_style_lang=' + lang + '; expires=Fri, 31 Dec 9999 23:59:59 GMT; path=/';
        }}

        // 加载语言偏好
        function loadLang() {{
            const cookie = document.cookie.split('; ').find(row => row.startsWith('fy_style_lang='));
            const lang = cookie ? cookie.split('=')[1] : 'cn';
            if (langPacks[lang]) {{
                currentLang = lang;
                currentLangPack = langPacks[lang];
            }} else {{
                // 如果保存的语言包不存在，回退到第一个可用的语言
                const availableLangs = Object.keys(langPacks);
                currentLang = availableLangs[0];
                currentLangPack = langPacks[currentLang];
            }}
            langToggle.textContent = getLangDisplay(currentLang);
            langToggle.style.fontWeight = currentLang === 'cn' ? 'bold' : 'normal';
        }}

        // 应用语言
        function applyLang() {{
            const pack = currentLangPack;
            // 更新所有 data-i18n 元素
            document.querySelectorAll('[data-i18n]').forEach(el => {{
                const key = el.getAttribute('data-i18n');
                if (pack.base && pack.base[key]) el.textContent = pack.base[key];
            }});
            // 更新 placeholder
            document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {{
                const key = el.getAttribute('data-i18n-placeholder');
                if (pack.placeholder && pack.placeholder[key]) el.placeholder = pack.placeholder[key];
            }});
            // 更新 no-result 提示
            const noResult = gridContainer.querySelector('.no-result');
            if (noResult) noResult.textContent = pack.base.no_result;
            // 更新选项卡（全部和分类）
            updateTabLabels();
            // 更新按钮 title
            updateButtonTitles(pack);
            // 更新提示条文本（如果已显示）
            updateSelectionTipText(pack);
            // 更新 columnsSelect 选项
            updateColumnsSelect(pack);
            // 更新结果计数
            updateResultCount();
        }}

        // 更新按钮 title
        function updateButtonTitles(pack) {{
            if (pack.base) {{
                const langToggle = document.getElementById('langToggle');
                const themeToggle = document.getElementById('themeToggle');
                const newWindowBtn = document.querySelector('[data-i18n="new_window_btn"]');
                const locateIcon = document.querySelector('.locate-icon');
                
                if (langToggle && pack.base.lang_toggle_title) {{
                    langToggle.title = pack.base.lang_toggle_title;
                }}
                if (themeToggle && pack.base.theme_toggle_title) {{
                    themeToggle.title = pack.base.theme_toggle_title;
                }}
                if (newWindowBtn && pack.base.new_window_title) {{
                    newWindowBtn.title = pack.base.new_window_title;
                }}
                if (locateIcon && pack.base.locate_icon_title) {{
                    locateIcon.title = pack.base.locate_icon_title;
                }}
            }}
        }}

        // 更新提示条文本
        function updateSelectionTipText(pack) {{
            if (pack.base && selectionTip.style.display === 'flex' && selectedCardData) {{
                tipText.textContent = `${{pack.base.selected_tip}} "${{selectedCardData.data.desc}}"`;
            }}
        }}

        // 更新 columnsSelect 选项
        function updateColumnsSelect(pack) {{
            if (pack.columns) {{
                const options = columnsSelect.options;
                for (let i = 0; i < options.length; i++) {{
                    const value = options[i].value;
                    if (pack.columns[value]) {{
                        options[i].text = pack.columns[value];
                    }}
                }};
            }}
        }}

        // 更新选项卡标签
        function updateTabLabels() {{
            const allBtn = tabsContainer.querySelector('.tab-btn');
            if (allBtn) {{
                allBtn.innerText = currentLangPack.base.all;
            }}
            // 更新分类标签
            const categoryBtns = tabsContainer.querySelectorAll('.tab-btn:not(:first-child)');
            categoryBtns.forEach(btn => {{
                const catKey = btn.getAttribute('data-key');
                if (catKey && currentLangPack.classify && currentLangPack.classify[catKey]) {{
                    btn.innerText = currentLangPack.classify[catKey];
                }}
            }});
        }}

        // 更新结果计数显示
        function updateResultCount() {{
            setResultCount(currentCategory, gridContainer.querySelectorAll('.card').length);
        }}
        
        // 设置结果计数显示（使用语言包）
        function setResultCount(category, count) {{
            const pack = currentLangPack;
            // 获取当前选中 tab 的文本作为分类名称
            let categoryName = category;
            const activeBtn = tabsContainer.querySelector('.tab-btn.active');
            if (activeBtn) {{
                categoryName = activeBtn.innerText;
            }}
            const countStr = pack.base.result_count ? pack.base.result_count.replace('{{0}}', count) : `${{count}}`;
            resultCountDiv.innerText = `${{categoryName}} - ${{countStr}}`;
        }}
        
        // 更新列数下拉选项
        function updateColumnsSelect() {{
            const options = columnsSelect.options;
            for (let i = 0; i < options.length; i++) {{
                const val = options[i].value;
                if (currentLangPack.columns && currentLangPack.columns[val]) {{
                    options[i].textContent = currentLangPack.columns[val];
                }}
            }}
        }}

        // 切换列数
        function changeColumns(cols) {{
            currentColumns = parseInt(cols);
            const cardWidth = `calc(100%/${{currentColumns}} - ${{(currentColumns-1)*10/currentColumns}}px)`;
            document.querySelectorAll('.card').forEach(card => {{
                card.style.width = cardWidth;
            }});
            saveColumns(currentColumns);
        }}

        // 保存列数到 cookie
        function saveColumns(cols) {{
            document.cookie = 'fy_style_columns=' + cols + '; expires=Fri, 31 Dec 9999 23:59:59 GMT; path=/';
        }}

        // 加载列数
        function loadColumns() {{
            const cookie = document.cookie.split('; ').find(row => row.startsWith('fy_style_columns='));
            const cols = cookie ? parseInt(cookie.split('=')[1]) : 4;
            currentColumns = cols;
            columnsSelect.value = cols;
            const cardWidth = `calc(100%/${{cols}} - ${{(cols-1)*10/cols}}px)`;
            document.querySelectorAll('.card').forEach(card => {{
                card.style.width = cardWidth;
            }});
        }}

        // 渲染选项卡
        function renderTabs() {{
            const allBtn = document.createElement('button');
            allBtn.className = 'tab-btn active';
            allBtn.innerText = currentLangPack.base.all;
            allBtn.onclick = () => switchTab('全部', null, allBtn);
            tabsContainer.appendChild(allBtn);

            categories.forEach(tag => {{
                const btn = document.createElement('button');
                btn.className = 'tab-btn';
                btn.setAttribute('data-key', tag);
                // 优先使用语言包中的 classify 名称
                let displayName = tag;
                if (currentLangPack.classify && currentLangPack.classify[tag]) {{
                    displayName = currentLangPack.classify[tag];
                }} else if (categoryNameMap[tag]) {{
                    displayName = categoryNameMap[tag];
                }}
                btn.innerText = displayName;
                btn.onclick = () => switchTab(tag, tag, btn);
                tabsContainer.appendChild(btn);
            }});
        }}

        // 渲染图片网格
        function renderGrid(list) {{
            gridContainer.innerHTML = '';
            setResultCount(currentCategory, list.length);
            if (list.length === 0) {{
                gridContainer.innerHTML = '<div class="no-result" data-i18n="no_result">找不到内容</div>';
                return;
            }}
            const cardWidth = `calc(100%/${{currentColumns}} - ${{(currentColumns-1)*10/currentColumns}}px)`;
            list.forEach(img => {{
                // 使用 DOM 元素创建代替字符串拼接，彻底解决路径和变量作用域问题
                const card = document.createElement('div');
                card.className = 'card';
                card.style.width = cardWidth;
                card.onclick = (e) => selectCard(card, e, img);

                // 1. 放大镜
                const zoomIcon = document.createElement('div');
                zoomIcon.className = 'zoom-icon';
                zoomIcon.innerHTML = '<svg viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></path></svg>';
                zoomIcon.onclick = (e) => {{
                    e.stopPropagation();
                    openModal(img);
                }};
                card.appendChild(zoomIcon);

                // 2. 序号标签
                const indexTag = document.createElement('div');
                indexTag.className = 'index-tag';
                indexTag.innerText = img.index;
                card.appendChild(indexTag);

                // 3. 选中标记
                const checkmark = document.createElement('div');
                checkmark.className = 'card-checkmark';
                checkmark.innerHTML = '<svg viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg"><path class="card-checkmark-bg" d="M1023.60039 0.802217H0.601413L1023.60039 1023.800195V0.802217z"></path><path class="card-checkmark-icon" d="M910.993358 164.092753a46.239844 46.239844 0 0 0-32.568195 13.26105l-0.052948 0.051949-214.106912 214.106911-90.861268-90.861268-0.111891-0.107895a46.186896 46.186896 0 0 0-65.306224 65.306225l0.107895 0.111891 123.684214 123.684214 0.111891 0.107895a46.184898 46.184898 0 0 0 31.998751 12.938365l0.268738 0.002997a46.186896 46.186896 0 0 0 32.479282-12.936367l0.109892-0.105897 242.018654-241.890778h0.15385l5.018099-5.143977a46.242841 46.242841 0 0 0-0.466544-65.04448 46.238845 46.238845 0 0 0-32.477284-13.480835z"></path></svg>';
                card.appendChild(checkmark);

                // 4. 图片容器
                const imgWrapper = document.createElement('div');
                imgWrapper.className = 'img-wrapper';
                const imgEl = document.createElement('img');
                imgEl.src = '{{web_img_dir}}/' + encodeURIComponent(img.filename);
                imgEl.alt = img.desc;
                imgEl.loading = 'lazy';
                imgWrapper.appendChild(imgEl);
                card.appendChild(imgWrapper);

                // 4. 信息区
                const infoDiv = document.createElement('div');
                infoDiv.className = 'info';
                const titleDiv = document.createElement('div');
                titleDiv.className = 'info-title';
                titleDiv.title = img.desc;
                titleDiv.innerText = img.desc;
                const promptDiv = document.createElement('div');
                promptDiv.className = 'info-prompt';
                promptDiv.title = img.prompt;
                promptDiv.innerText = img.prompt;
                
                // 添加隐藏的负向提示词节点
                const negativePromptDiv = document.createElement('div');
                negativePromptDiv.className = 'info-prompt-negative';
                negativePromptDiv.innerText = img.negative_prompt || '';
                
                // 添加隐藏的 URL 节点
                const urlDiv = document.createElement('div');
                urlDiv.className = 'info-url';
                urlDiv.style.display = 'none';
                urlDiv.innerText = img.url || '';
                
                infoDiv.appendChild(titleDiv);
                infoDiv.appendChild(promptDiv);
                infoDiv.appendChild(negativePromptDiv);
                infoDiv.appendChild(urlDiv);
                card.appendChild(infoDiv);

                gridContainer.appendChild(card);
            }});
            // 切换分类后恢复选中状态：在已渲染的卡片中按 filename 匹配，重新添加 .s
            if (selectedCardData && selectedCardData.data && selectedCardData.data.filename) {{
                const prevFilename = selectedCardData.data.filename;
                let restored = null;
                gridContainer.querySelectorAll('.card').forEach(c => {{
                    const imgEl = c.querySelector('.img-wrapper img');
                    if (imgEl && imgEl.src.endsWith(encodeURIComponent(prevFilename))) {{
                        restored = c;
                    }}
                }});
                if (restored) {{
                    restored.classList.add('s');
                    selectedCardData = {{ card: restored, data: selectedCardData.data }};
                    tipText.textContent = `${{currentLangPack.base.selected_tip}} "${{selectedCardData.data.desc}}"`;
                    selectionTip.style.display = 'flex';
                }} else {{
                    // 当前分类下没有该图片，清除选中状态
                    selectedCardData = null;
                    selectionTip.style.display = 'none';
                }}
            }}
        }}

        // 切换选项卡
        function switchTab(category, tag, btnElement) {{
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            btnElement.classList.add('active');
            currentCategory = category;
            currentTag = tag;
            searchInput.value = '';
            applyFilters();
        }}

        // 点击查询按钮
        function handleSearch() {{
            applyFilters();
        }}

        // 点击重置按钮
        function handleReset() {{
            searchInput.value = '';
            currentCategory = '全部';
            currentTag = null;
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelector('.tab-btn').classList.add('active');
            applyFilters();
        }}

        // 核心过滤逻辑
        function applyFilters() {{
            const keyword = searchInput.value.trim().toLowerCase();
            let filtered = images;
            if (currentTag) {{
                filtered = filtered.filter(img => img.tag === currentTag);
            }}
            if (keyword) {{
                filtered = filtered.filter(img => img.desc.toLowerCase().includes(keyword) || img.prompt.toLowerCase().includes(keyword) );
            }}
            renderGrid(filtered);
        }}

        // 卡片点击选择逻辑
        function selectCard(clickedCard, event, imgData) {{
            event.stopPropagation(); // 防止事件冒泡

            // 如果点击的是已选中的卡片（取消选择）
            if (clickedCard.classList.contains('s')) {{
                clickedCard.classList.remove('s');
                selectionTip.style.display = 'none';
                selectedCardData = null;
                // 发送取消选择消息
                if (window.parent) {{
                    window.parent.postMessage({{
                        type: 'FY_STYLE_SELECT',
                        filename: null,
                        desc: '',
                        prompt: '',
                        negative_prompt: ''
                    }}, '*');
                }}
                return;
            }}

            // 取消其他卡片的选中状态
            document.querySelectorAll('.card.s').forEach(card => {{
                card.classList.remove('s');
            }});

            // 选中当前卡片
            clickedCard.classList.add('s');

            // 更新提示条
            tipText.textContent = `${{currentLangPack.base.selected_tip}} "${{imgData.desc}}"`;
            selectionTip.style.display = 'flex'; // 显示提示条
            selectedCardData = {{ card: clickedCard, data: imgData }};

            // 发送选择消息给父窗口（ComfyUI）
            if (window.parent) {{
                window.parent.postMessage({{
                    type: 'FY_STYLE_SELECT',
                    filename: imgData.filename,
                    desc: imgData.desc,
                    prompt: imgData.prompt,
                    negative_prompt: imgData.negative_prompt
                }}, '*');
            }}
        }}

        // 打开模态框
        function openModal(imgData) {{
            modalImage.src = '{{web_img_dir}}/' + encodeURIComponent(imgData.filename);
            modalTitle.innerText = imgData.desc;
            // 动态创建提示词节点，仅在有内容时输出
            let positiveWrapper = document.getElementById('modalPromptWrapper');
            if (imgData.prompt && imgData.prompt.trim()) {{
                if (!positiveWrapper) {{
                    positiveWrapper = document.createElement('div');
                    positiveWrapper.id = 'modalPromptWrapper';
                    positiveWrapper.className = 'modal-prompt-wrapper';
                    positiveWrapper.innerHTML = '<span id=\"modalPrompt\" class=\"modal-prompt\"></span><span class=\"copy-icon\" onclick=\"copyToClipboard(document.getElementById(\\'modalPrompt\\').innerText)\"><svg viewBox=\"0 0 24 24\" width=\"14\" height=\"14\"><path d=\"M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z\"/></path></svg></span>';
                    modalTitle.parentNode.appendChild(positiveWrapper);
                }}
                document.getElementById('modalPrompt').innerText = imgData.prompt;
            }} else if (positiveWrapper) {{
                positiveWrapper.remove();
            }}
            let negativeWrapper = document.getElementById('modalPromptNegativeWrapper');
            if (imgData.negative_prompt && imgData.negative_prompt.trim()) {{
                if (!negativeWrapper) {{
                    negativeWrapper = document.createElement('div');
                    negativeWrapper.id = 'modalPromptNegativeWrapper';
                    negativeWrapper.className = 'modal-prompt-wrapper';
                    negativeWrapper.innerHTML = '<span id=\"modalPromptNegative\" class=\"modal-prompt-negative\"></span><span class=\"copy-icon\" onclick=\"copyToClipboard(document.getElementById(\\'modalPromptNegative\\').innerText)\"><svg viewBox=\"0 0 24 24\" width=\"14\" height=\"14\"><path d=\"M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z\"/></path></svg></span>';
                    modalTitle.parentNode.appendChild(negativeWrapper);
                }}
                document.getElementById('modalPromptNegative').innerText = imgData.negative_prompt;
            }} else if (negativeWrapper) {{
                negativeWrapper.remove();
            }}
            // 在标题后面添加 URL 超链接图标，如果存在的话
            const existingLink = document.getElementById('modalUrlLinkWrapper');
            if (existingLink) existingLink.remove();
            if (imgData.url && imgData.url.trim()) {{
                const urlLink = document.createElement('a');
                urlLink.id = 'modalUrlLinkWrapper';
                urlLink.href = imgData.url;
                urlLink.target = '_blank';
                urlLink.innerHTML = '<svg t="1784914401910" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="10494" width="200" height="200"><path d="M567.168 168.96a203.562667 203.562667 0 1 1 287.872 287.872l-129.28 129.28-60.373333-60.288 129.28-129.322667a118.229333 118.229333 0 1 0-167.168-167.253333l-129.322667 129.322667-60.330667-60.330667 129.28-129.28z m90.453333 257.706667l-231.04 230.997333L366.250667 597.333333l230.997333-230.997333L657.621333 426.666667z m-299.093333 71.509333l-129.28 129.322667a118.229333 118.229333 0 1 0 167.253333 167.253333l129.28-129.322667 60.330667 60.330667-129.28 129.28a203.562667 203.562667 0 1 1-287.914667-287.872l129.28-129.28 60.373334 60.288z" p-id="10495" fill="#ffffff"></path></svg>';
                urlLink.title = imgData.url;
                modalTitle.appendChild(urlLink);
            }}
            imageModal.style.display = 'flex';
        }}

        // 关闭模态框
        function closeModal() {{
            imageModal.style.display = 'none';
        }}

        // 复制到剪贴板
        function copyToClipboard(text) {{
            if (!text || !text.trim()) return;
            navigator.clipboard.writeText(text).then(() => {{
                // 简单的复制成功提示
                const tip = document.createElement('div');
                tip.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,0.8);color:#fff;padding:10px 20px;border-radius:4px;font-size:14px;z-index:2000;';
                tip.innerText = currentLangPack.base.copy_success;
                document.body.appendChild(tip);
                setTimeout(() => tip.remove(), 1500);
            }}).catch(err => {{
                console.error('复制失败:', err);
            }});
        }}

        // 点击背景关闭
        imageModal.onclick = function(event) {{
            if (event.target === imageModal) closeModal();
        }}

        // 回车搜索
        searchInput.addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') handleSearch();
        }});

        // 新增：滚动到选中卡片
        function scrollToCard() {{
            if (!selectedCardData) return;
            // 查找当前视图中对应的卡片元素
            const cards = gridContainer.querySelectorAll('.card');
            let targetCard = null;
            for (let card of cards) {{
                const imgElement = card.querySelector('.img-wrapper img');
                // 修复点：使用 selectedCardData.data.desc 而不是 selectedCardData.desc
                if (imgElement && imgElement.alt === selectedCardData.data.desc) {{
                    targetCard = card;
                    break;
                }}
            }}
            if (targetCard) {{
                targetCard.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                // 可选：添加一个临时的视觉反馈
                targetCard.style.boxShadow = '0 0 15px rgba(0, 0, 0, 0.33)';
                setTimeout(() => {{
                    targetCard.style.boxShadow = 'none';
                }}, 2000);
            }}
        }}

        // 绑定定位图标的点击事件
        locateIcon.onclick = scrollToCard;

        // 在新窗口中打开
        function openInNewWindow() {{
            window.open('/fy-style', '_blank');
        }}

        // 主题切换功能
        function toggleTheme() {{
            const root = document.documentElement;
            const icon = document.getElementById('themeIcon');
            if (root.classList.contains('dark')) {{
                root.classList.remove('dark');
                icon.innerHTML = '<path d="M20 8.69V4h-4.69L12 .69 8.69 4H4v4.69L.69 12 4 15.31V20h4.69L12 23.31 15.31 20H20v-4.69L23.31 12 20 8.69zM12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6 6 2.69 6 6-2.69 6-6 6zm0-10c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4z"/>';
                saveTheme('light');
                // 更新提示条样式
                selectionTip.classList.remove('dark');
            }} else {{
                root.classList.add('dark');
                icon.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
                saveTheme('dark');
                // 更新提示条样式
                selectionTip.classList.add('dark');
            }}
        }}

        function saveTheme(theme) {{
            document.cookie = 'fy_style_theme=' + theme + '; expires=Fri, 31 Dec 9999 23:59:59 GMT; path=/';
        }}

        function loadTheme() {{
            const cookie = document.cookie.split('; ').find(row => row.startsWith('fy_style_theme='));
            const theme = cookie ? cookie.split('=')[1] : 'light';
            const root = document.documentElement;
            const icon = document.getElementById('themeIcon');
            if (theme === 'dark') {{
                root.classList.add('dark');
                icon.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
            }} else {{
                root.classList.remove('dark');
                icon.innerHTML = '<path d="M20 8.69V4h-4.69L12 .69 8.69 4H4v4.69L.69 12 4 15.31V20h4.69L12 23.31 15.31 20H20v-4.69L23.31 12 20 8.69zM12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6 6 2.69 6 6-2.69 6-6 6zm0-10c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4z"/>';
            }}
        }}

        // 初始化主题
        loadTheme();

        // 初始化语言
        loadLang();
        applyLang();

        // 初始化列数
        loadColumns();

        // 初始化
        renderTabs();
        renderGrid(images);
        
        // 修复点：初始化时确保提示框隐藏
        selectionTip.style.display = 'none';

        // 自动定位到已选中的卡片
        function autoLocateSelected(filename) {{
            if (!filename) return;
            const cards = gridContainer.querySelectorAll('.card');
            let targetCard = null;
            // src 格式: /fy-style/img/<encodeURIComponent(filename)>，提取并解码后比较
            for (let i = 0; i < cards.length; i++) {{
                const card = cards[i];
                const imgElement = card.querySelector('.img-wrapper img');
                if (imgElement) {{
                    const srcFilename = decodeURIComponent(imgElement.src.split('/').pop());
                    if (srcFilename === filename) {{
                        targetCard = card;
                        break;
                    }}
                }}
            }}
            if (targetCard) {{
                const descMatch = filename.match(/\\](\\d+)-(.+?)\\(/);
                const desc = descMatch ? descMatch[2] : filename;
                targetCard.classList.add('s');
                tipText.textContent = `${{currentLangPack.base.selected_tip}} "${{desc}}"`;
                selectionTip.style.display = 'flex';
                selectedCardData = {{ card: targetCard, data: {{ desc: desc }} }};
                targetCard.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                targetCard.style.boxShadow = '0 0 15px rgba(0, 0, 0, 0.33)';
                setTimeout(() => {{ targetCard.style.boxShadow = 'none'; }}, 2000);
            }}
        }}

        // 禁止拖拽图片
        document.addEventListener('dragstart', function(e) {{
            if (e.target.tagName === 'IMG') {{
                e.preventDefault();
            }}
        }});

        // 禁止右键菜单（搜索框除外）
        document.addEventListener('contextmenu', function(e) {{
            if (e.target.id !== 'searchInput') {{
                e.preventDefault();
            }}
        }});

        // 页面加载时自动定位：优先从 URL 参数读取，否则轮询 API
        (function initAutoLocate() {{
            const params = new URLSearchParams(window.location.search);
            const urlValue = params.get('v');
            if (urlValue) {{
                autoLocateSelected(urlValue.split('|')[0]);
                return;
            }}
            // URL 无参数，轮询 API（兼容直接访问 /fy-style 的场景）
            let attempts = 0;
            const maxAttempts = 30;
            const pollInterval = setInterval(() => {{
                attempts++;
                fetch('/fy-style/selected-image')
                    .then(res => res.json())
                    .then(data => {{
                        if (data && data.value) {{
                            const filename = data.value.split('|')[0];
                            autoLocateSelected(filename);
                            clearInterval(pollInterval);
                        }} else if (data && data.filename) {{
                            autoLocateSelected(data.filename);
                            clearInterval(pollInterval);
                        }} else if (attempts >= maxAttempts) {{
                            clearInterval(pollInterval);
                        }}
                    }})
                    .catch(() => {{
                        if (attempts >= maxAttempts) clearInterval(pollInterval);
                    }});
            }}, 200);
        }})();
    </script>
</body>
</html>"""

    return html_template

def main():
    # 加载语言包
    lang_packs = load_language_packs()
    if not lang_packs:
        print("警告：未加载到任何语言包，使用默认语言")
        lang_packs = {'zh-cn': {}}  # 空语言包，避免崩溃

    if not os.path.exists(IMG_DIR):
        print(f"错误：找不到 '{IMG_DIR}' 文件夹，请在同级目录下创建它并放入图片。")
        return

    image_files = [f for f in os.listdir(IMG_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    parsed_images = []
    for f in image_files:
        data = parse_filename(f, lang_packs)
        if data:
            parsed_images.append(data)
        else:
            print(f"警告：无法解析文件名，已跳过 -> {f}")

    if not parsed_images:
        print("未找到符合命名规范的图片。")
        return

    # 提取所有不重复的 tag（用于语言包和前端 tab）
    categories = sorted(list(set(img["tag"] for img in parsed_images if img["tag"])))
    category_counts = {tag: sum(1 for img in parsed_images if img.get("tag") == tag) for tag in categories}

    # 将分类数据合并到语言包中
    merge_classify_into_lang(lang_packs, category_counts)

    html_content = generate_html(parsed_images, lang_packs, categories, category_counts)
    html_content = html_content.replace('{web_img_dir}', WEB_IMG_DIR)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"成功生成 {OUTPUT_FILE}！共处理 {len(parsed_images)} 张图片。")
    print("请在浏览器中打开 index.html 查看效果。")

if __name__ == "__main__":
    main()