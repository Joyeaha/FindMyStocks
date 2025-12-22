/**
 * 筛选项配置弹窗模块
 * 负责管理筛选项的配置界面和逻辑
 */

(function () {
  "use strict";

  // 弹窗元素引用
  let modal = null;
  let filterFieldsList = null;
  let addFilterFieldBtn = null;
  let saveConfigBtn = null;
  let cancelConfigBtn = null;
  let testApiBtn = null;
  let apiTestResult = null;
  let apiTestResultContent = null;
  let modalTitle = null;

  // 当前编辑的筛选项配置（临时状态）
  let currentConfig = [];

  // 正在编辑的行索引（-1 表示没有正在编辑的行）
  let editingIndex = -1;

  // 配置类型：'fundamental' 或 'fs'
  let configType = "fundamental";

  /**
   * 初始化弹窗模块
   */
  function init() {
    // 获取元素引用（共用同一个弹窗）
    modal = document.getElementById("filterConfigModal");
    filterFieldsList = document.getElementById("filterFieldsList");
    addFilterFieldBtn = document.getElementById("addFilterFieldBtn");
    saveConfigBtn = document.getElementById("saveConfigBtn");
    cancelConfigBtn = document.getElementById("cancelConfigBtn");
    testApiBtn = document.getElementById("testApiBtn");
    apiTestResult = document.getElementById("apiTestResult");
    apiTestResultContent = document.getElementById("apiTestResultContent");
    modalTitle = document.getElementById("filterConfigModalTitle");

    if (
      !modal ||
      !filterFieldsList ||
      !addFilterFieldBtn ||
      !saveConfigBtn ||
      !cancelConfigBtn ||
      !testApiBtn ||
      !apiTestResult ||
      !apiTestResultContent ||
      !modalTitle
    ) {
      console.error("筛选项配置弹窗元素未找到");
      return;
    }

    // 绑定事件
    addFilterFieldBtn.addEventListener("click", addNewFilterField);
    saveConfigBtn.addEventListener("click", saveConfig);
    cancelConfigBtn.addEventListener("click", closeModal);
    testApiBtn.addEventListener("click", testApi);

    // 绑定基本面配置按钮
    const fundamentalBtn = document.getElementById(
      "fundamentalFilterSettingBtn"
    );
    if (fundamentalBtn) {
      fundamentalBtn.addEventListener("click", () => {
        configType = "fundamental";
        openModal();
      });
    }

    // 绑定财报配置按钮
    const fsBtn = document.getElementById("fsFilterSettingBtn");
    if (fsBtn) {
      fsBtn.addEventListener("click", () => {
        configType = "fs";
        openModal();
      });
    }

    // 点击弹窗背景关闭
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        closeModal();
      }
    });

    // ESC 键关闭弹窗
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && modal && !modal.classList.contains("hidden")) {
        closeModal();
      }
    });
  }

  /**
   * 打开弹窗
   */
  function openModal() {
    if (!modal) return;

    // 更新弹窗标题
    if (modalTitle) {
      modalTitle.textContent =
        configType === "fundamental" ? "基本面筛选项配置" : "财报筛选项配置";
    }

    // 加载当前配置
    loadCurrentConfig();

    // 显示弹窗
    modal.classList.remove("hidden");
    modal.style.display = "flex";
    modal.classList.add("flex"); // 确保 flex 布局生效
    document.body.style.overflow = "hidden"; // 防止背景滚动
  }

  /**
   * 关闭弹窗
   */
  function closeModal() {
    if (!modal) return;

    // 隐藏弹窗
    modal.classList.add("hidden");
    modal.style.display = "none";
    document.body.style.overflow = ""; // 恢复滚动

    // 隐藏API测试结果
    if (apiTestResult) {
      apiTestResult.classList.add("hidden");
    }

    // 重置配置（不保存）
    currentConfig = [];
    editingIndex = -1;
  }

  /**
   * 加载当前配置
   */
  function loadCurrentConfig() {
    // 根据类型从全局变量获取当前配置
    let globalFilterFields = [];
    if (configType === "fundamental") {
      globalFilterFields =
        window.FILTER_FIELDS ||
        (typeof FILTER_FIELDS !== "undefined" ? FILTER_FIELDS : []);
    } else if (configType === "fs") {
      globalFilterFields =
        window.FS_FILTER_FIELDS ||
        (typeof FS_FILTER_FIELDS !== "undefined" ? FS_FILTER_FIELDS : []);
    }

    if (globalFilterFields && globalFilterFields.length > 0) {
      currentConfig = JSON.parse(JSON.stringify(globalFilterFields));
    } else {
      currentConfig = [];
    }

    // 渲染配置列表
    renderFilterFieldsList();
  }

  /**
   * 渲染筛选项列表
   */
  function renderFilterFieldsList() {
    if (!filterFieldsList) return;

    // 清空列表（保留表头）
    const header = filterFieldsList.querySelector(".grid");
    filterFieldsList.innerHTML = "";
    if (header) {
      filterFieldsList.appendChild(header);
    } else {
      // 如果没有表头，重新创建
      const headerDiv = document.createElement("div");
      headerDiv.className =
        "grid grid-cols-3 gap-4 mb-2 pb-2 border-b border-gray-200";
      headerDiv.innerHTML = `
        <div class="font-semibold text-sm text-gray-700">筛选项名称</div>
        <div class="font-semibold text-sm text-gray-700">理杏仁指标</div>
        <div class="font-semibold text-sm text-gray-700">操作</div>
      `;
      filterFieldsList.appendChild(headerDiv);
    }

    // 渲染每个筛选项
    currentConfig.forEach((field, index) => {
      const row = createFilterFieldRow(field, index);
      filterFieldsList.appendChild(row);
    });
  }

  /**
   * 创建筛选项行
   */
  function createFilterFieldRow(field, index) {
    const row = document.createElement("div");
    row.className =
      "grid grid-cols-3 gap-4 items-center py-2 border-b border-gray-100";
    row.dataset.index = index;

    // 判断是否为编辑模式或新添加的项（没有 key 和 label）
    const isNewItem = !field.key && !field.label;
    const isEditing = editingIndex === index;

    if (isEditing || isNewItem) {
      // 编辑模式：显示输入框 + 确定按钮 + 取消按钮
      return createEditModeRow(field, index, row, isNewItem);
    } else {
      // 显示模式：显示文本 + 修改按钮 + 删除按钮
      return createDisplayModeRow(field, index, row);
    }
  }

  /**
   * 创建显示模式的行（文本 + 修改按钮 + 删除按钮）
   */
  function createDisplayModeRow(field, index, row) {
    // 筛选项名称（文本）
    const labelText = document.createElement("div");
    labelText.className = "text-sm text-gray-700";
    labelText.textContent = field.label || "";

    // 理杏仁指标（文本）
    const keyText = document.createElement("div");
    keyText.className = "text-sm text-gray-700";
    keyText.textContent = field.key || "";

    // 操作按钮容器
    const buttonsContainer = document.createElement("div");
    buttonsContainer.className = "flex items-center gap-2";

    // 修改按钮（铅笔图标）
    const editBtn = document.createElement("button");
    editBtn.className =
      "p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors";
    editBtn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
      </svg>
    `;
    editBtn.addEventListener("click", () => {
      enterEditMode(index);
    });

    // 删除按钮（垃圾桶图标）
    const deleteBtn = document.createElement("button");
    deleteBtn.className =
      "p-1 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded transition-colors";
    deleteBtn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="3 6 5 6 21 6"></polyline>
        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
      </svg>
    `;
    deleteBtn.addEventListener("click", () => {
      deleteFilterField(index);
    });

    buttonsContainer.appendChild(editBtn);
    buttonsContainer.appendChild(deleteBtn);

    row.appendChild(labelText);
    row.appendChild(keyText);
    row.appendChild(buttonsContainer);

    return row;
  }

  /**
   * 创建编辑模式的行（输入框 + 确定按钮 + 取消按钮）
   */
  function createEditModeRow(field, index, row, isNewItem) {
    // 保存原始值（用于取消时恢复）
    const originalField = {
      key: field.key || "",
      label: field.label || "",
    };

    // 筛选项名称输入框
    const labelInput = document.createElement("input");
    labelInput.type = "text";
    labelInput.className =
      "text-sm px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-300 focus:ring-2 focus:ring-blue-200";
    labelInput.placeholder = "筛选项名称";
    labelInput.value = field.label || "";

    // 理杏仁指标输入框
    const keyInput = document.createElement("input");
    keyInput.type = "text";
    keyInput.className =
      "text-sm px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-300 focus:ring-2 focus:ring-blue-200";
    keyInput.placeholder = "理杏仁指标（如：pe_ttm）";
    keyInput.value = field.key || "";

    // 操作按钮容器
    const buttonsContainer = document.createElement("div");
    buttonsContainer.className = "flex items-center gap-2";

    // 确定按钮的处理函数
    const handleConfirm = () => {
      const newLabel = labelInput.value.trim();
      const newKey = keyInput.value.trim();

      // 验证必填字段
      if (!newLabel || !newKey) {
        alert("筛选项名称和理杏仁指标都不能为空");
        return;
      }

      // 检查 key 是否与其他配置项冲突（排除当前项）
      const keyConflict = currentConfig.some((field, i) => {
        return i !== index && field.key && field.key.trim() === newKey;
      });
      if (keyConflict) {
        alert(`理杏仁指标 "${newKey}" 已存在，不能重复`);
        return;
      }

      // 检查 label 是否与其他配置项冲突（排除当前项）
      const labelConflict = currentConfig.some((field, i) => {
        return i !== index && field.label && field.label.trim() === newLabel;
      });
      if (labelConflict) {
        alert(`筛选项名称 "${newLabel}" 已存在，不能重复`);
        return;
      }

      // 更新配置
      currentConfig[index].label = newLabel;
      currentConfig[index].key = newKey;

      // 自动更新 minId 和 maxId
      currentConfig[index].minId = `${newKey}Min`;
      currentConfig[index].maxId = `${newKey}Max`;

      // 退出编辑模式
      editingIndex = -1;
      renderFilterFieldsList();
    };

    // 确定按钮
    const confirmBtn = document.createElement("button");
    confirmBtn.className =
      "px-3 py-1 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors";
    confirmBtn.textContent = "确定";
    confirmBtn.addEventListener("click", handleConfirm);

    // 为输入框添加回车键事件
    labelInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleConfirm();
      }
    });

    keyInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleConfirm();
      }
    });

    // 取消按钮
    const cancelBtn = document.createElement("button");
    cancelBtn.className =
      "px-3 py-1 text-sm text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded transition-colors";
    cancelBtn.textContent = "取消";
    cancelBtn.addEventListener("click", () => {
      if (isNewItem) {
        // 如果是新添加的项，取消时删除它
        currentConfig.splice(index, 1);
      } else {
        // 恢复原始值
        currentConfig[index].key = originalField.key;
        currentConfig[index].label = originalField.label;
      }

      // 退出编辑模式
      editingIndex = -1;
      renderFilterFieldsList();
    });

    buttonsContainer.appendChild(confirmBtn);
    buttonsContainer.appendChild(cancelBtn);

    row.appendChild(labelInput);
    row.appendChild(keyInput);
    row.appendChild(buttonsContainer);

    // 如果是新添加的项，自动聚焦到第一个输入框
    if (isNewItem) {
      setTimeout(() => labelInput.focus(), 100);
    } else {
      setTimeout(() => keyInput.focus(), 100);
    }

    return row;
  }

  /**
   * 进入编辑模式
   */
  function enterEditMode(index) {
    editingIndex = index;
    renderFilterFieldsList();
  }

  /**
   * 添加新筛选项
   */
  function addNewFilterField() {
    // 如果有正在编辑的行，先退出编辑模式
    if (editingIndex !== -1) {
      editingIndex = -1;
    }

    const newField = {
      key: "",
      label: "",
      minId: "",
      maxId: "",
    };

    // 添加到列表顶部（表头之后）
    currentConfig.unshift(newField);
    editingIndex = 0; // 新添加的项自动进入编辑模式

    // 重新渲染列表
    renderFilterFieldsList();
  }

  /**
   * 删除筛选项
   */
  function deleteFilterField(index) {
    if (confirm("确定要删除这个筛选项吗？")) {
      currentConfig.splice(index, 1);
      renderFilterFieldsList();
    }
  }

  /**
   * 测试API
   */
  async function testApi() {
    // 验证配置
    const validConfig = currentConfig.filter((field) => {
      return field.key && field.label;
    });

    if (validConfig.length === 0) {
      alert("至少需要配置一个筛选项才能测试API");
      return;
    }

    // 提取 metricsList（使用新的对象格式）
    const fundamentalMetrics = validConfig
      .map((field) => field.key.trim())
      .filter(Boolean);

    if (fundamentalMetrics.length === 0) {
      alert("没有有效的理杏仁指标");
      return;
    }

    // 使用新的对象格式：fundamental 和 fs
    const metricsList = {
      fundamental: configType === "fundamental" ? fundamentalMetrics : [],
      fs: configType === "fs" ? fundamentalMetrics : [],
    };

    // 显示加载状态
    testApiBtn.disabled = true;
    testApiBtn.textContent = "🔄 测试中...";
    apiTestResult.classList.remove("hidden");
    apiTestResultContent.textContent = "正在请求API...";

    try {
      // 获取当前日期
      const today = new Date();
      const date = `${today.getFullYear()}-${String(
        today.getMonth() + 1
      ).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

      // 发送API请求
      const response = await fetch("/api/filter", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          stockCodes: ["00700"],
          metricsList: metricsList,
          date: date,
        }),
      });

      // 解析响应
      const result = await response.json();

      // 检查是否有错误
      if (!response.ok || result.error) {
        // 如果有错误，显示错误信息
        const errorMsg = result.error || `HTTP错误!状态码: ${response.status}`;
        apiTestResultContent.textContent = `错误: 
        ${JSON.stringify(errorMsg, null, 2)}`;
        return;
      }

      // 格式化JSON显示（保持缩进）
      const formattedResult = JSON.stringify(result, null, 2);
      apiTestResultContent.textContent = formattedResult;
    } catch (error) {
      console.error("API测试失败:", error);
      // 显示错误信息
      apiTestResultContent.textContent = `错误: 
      ${JSON.stringify(error, null, 2)}`;
    } finally {
      // 恢复按钮状态
      testApiBtn.disabled = false;
      testApiBtn.textContent = "🧪 测试API";
    }
  }

  /**
   * 保存配置
   */
  async function saveConfig() {
    // 验证配置
    const validConfig = currentConfig.filter((field) => {
      return field.key && field.label;
    });

    // 检查是否有重复的 key
    const keys = validConfig.map((f) => f.key.trim());
    const uniqueKeys = new Set(keys);
    if (keys.length !== uniqueKeys.size) {
      alert("理杏仁指标不能重复");
      return;
    }

    // 检查是否有重复的 label
    const labels = validConfig.map((f) => f.label.trim());
    const uniqueLabels = new Set(labels);
    if (labels.length !== uniqueLabels.size) {
      alert("筛选项名称不能重复");
      return;
    }

    // 确保每个字段都有 minId 和 maxId
    validConfig.forEach((field) => {
      if (!field.minId && field.key) {
        field.minId = `${field.key.trim()}Min`;
      }
      if (!field.maxId && field.key) {
        field.maxId = `${field.key.trim()}Max`;
      }
    });

    // 发送请求到后端保存配置
    try {
      const response = await fetch("/api/filter-config", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          filterConfig: validConfig,
          type: configType,
        }),
      });

      // 等待响应并检查是否成功
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.error || `HTTP错误!状态码: ${response.status}`
        );
      }

      // 解析成功响应
      const result = await response.json();
      console.log("配置保存成功:", result);

      // 只有在后端返回成功响应后，才执行以下操作
      // 更新全局配置变量
      if (typeof window !== "undefined") {
        if (configType === "fundamental") {
          window.FILTER_FIELDS = validConfig;
        } else if (configType === "fs") {
          window.FS_FILTER_FIELDS = validConfig;
        }

        // 触发自定义事件，通知主页面配置已更新
        // 同时在 document 和 window 上触发事件，确保能被捕获
        const event = new CustomEvent("filterConfigUpdated", {
          detail: { config: validConfig, type: configType },
          bubbles: true, // 允许事件冒泡
          cancelable: true, // 允许取消事件
        });

        console.log("触发 filterConfigUpdated 事件", event);
        document.dispatchEvent(event);
        window.dispatchEvent(event); // 同时在 window 上触发
      }

      // 关闭弹窗
      closeModal();

      // 提示保存成功
      alert("配置已保存");
    } catch (error) {
      // 如果保存失败，不关闭弹窗，不更新配置
      console.error("保存配置失败:", error);
      alert(`保存配置失败: ${error.message}`);
    }
  }

  // DOM 加载完成后初始化
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
