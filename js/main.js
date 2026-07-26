import { app } from "../../../scripts/app.js";

// 存储所有 FY_Style 节点引用
const fyStyleNodes = [];

// 为 FY_Style 节点添加自定义 UI
function addFYStyleWidget(node) {
    // 创建 iframe 容器
    const container = document.createElement("div");
    container.style.cssText = "width:100%;height:100%;position:relative;overflow:hidden;";

    // 创建 iframe，初始 URL 不带参数
    const iframe = document.createElement("iframe");
    iframe.src = "/fy-style";
    iframe.style.cssText = "width:100%;height:100%;border:none;display:block;";
    iframe.allow = "cross-origin-isolated";

    container.appendChild(iframe);

    // 保存 iframe 引用到节点
    node._fyStyleIframe = iframe;

    // 添加 DOM 部件到节点
    node.addDOMWidget(
        "fy_style_view",
        "FY Style",
        container,
        {
            getMinHeight: () => 400,
            hideOnZoom: false,
            serialize: false
        }
    );

    // 保存节点引用
    fyStyleNodes.push(node);

    // 将 widget 值传给 iframe（节点创建时可能还未加载保存值，轮询等待）
    (function sendWidgetValueToIframe() {
        const widget = node.widgets?.find(w => w.name === 'selected_image');
        function trySend() {
            const val = widget?.value || '';
            if (val) {
                iframe.src = '/fy-style?v=' + encodeURIComponent(val);
            }
        }
        // 立即尝试
        trySend();
        // 如果为空，轮询等待（workflow 加载时 widget 值会更新）
        if (!widget?.value) {
            let attempts = 0;
            const interval = setInterval(() => {
                attempts++;
                trySend();
                if (widget?.value && iframe.src.includes('v=')) {
                    clearInterval(interval);
                } else if (attempts >= 50) {
                    clearInterval(interval);
                }
            }, 100);
        }
    })();
}

// 处理来自 iframe 的消息
function handleMessage(event) {
    if (event.data?.type === 'FY_STYLE_SELECT') {
        const { filename, desc, prompt, negative_prompt } = event.data;
        const widgetValue = (filename || '') + '|' + (prompt || '') + '|' + (negative_prompt || '');

        // 通过 event.source 匹配来源 iframe，只更新对应节点
        let targetNode = null;
        for (let i = 0; i < fyStyleNodes.length; i++) {
            if (fyStyleNodes[i]._fyStyleIframe && fyStyleNodes[i]._fyStyleIframe.contentWindow === event.source) {
                targetNode = fyStyleNodes[i];
                break;
            }
        }
        if (!targetNode) return;

        // 更新目标节点的输入值
        targetNode.widgets?.forEach(w => {
            if (w.name === 'selected_image') {
                w.value = widgetValue;
            }
            if (w.name === 'positive_prompt' && prompt !== undefined) {
                w.value = prompt;
            }
            if (w.name === 'negative_prompt' && negative_prompt !== undefined) {
                w.value = negative_prompt;
            }
        });

        // 触发画布重绘，使所有已更新的节点重新执行
        app.graph.setDirtyCanvas(true, true);
    }
}

// 监听节点创建事件
app.registerExtension({
    name: "FY.Style",
    async setup() {
        // 添加消息监听器
        window.addEventListener('message', handleMessage);
    },
    nodeCreated(node) {
        // 检查节点类型是否为 FY_Style
        if (node.constructor?.comfyClass === "FY_Style") {
            addFYStyleWidget(node);
        }
    },
    async beforeRegisterNodeDef(nodeType, nodeData) {
        // 在节点定义注册前添加清理逻辑
    },
    async remove() {
        // 清理消息监听器
        window.removeEventListener('message', handleMessage);
    }
});
