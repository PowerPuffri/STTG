const DEFAULT_CARD = {
  spec: "chara_card_v2",
  spec_version: "2.0",
  data: {
    name: "",
    description: "",
    personality: "",
    first_mes: "",
    avatar: "",
    mes_example: "",
    scenario: "",
    creator_notes: "",
    system_prompt: "",
    post_history_instructions: "",
    alternate_greetings: [],
    tags: [],
    creator: "",
    character_version: "",
    extensions: {},
    character_book: {
      name: "",
      description: "",
      scan_depth: 6,
      token_budget: 600,
      recursive_scanning: false,
      extensions: {},
      entries: []
    }
  }
};

const knownDataKeys = new Set(Object.keys(DEFAULT_CARD.data));

let extraRoot = {};
let extraData = {};
let stateExtensions = {};
let stateCharacterBook = structuredClone(DEFAULT_CARD.data.character_book);
let aiMode = "ai";
let selectedPlatform = "chub";

const ui = {
  fileInput: document.getElementById("fileInput"),
  importBtn: document.getElementById("importBtn"),
  exportBtn: document.getElementById("exportBtn"),
  copyBtn: document.getElementById("copyBtn"),
  refreshPreview: document.getElementById("refreshPreview"),
  validateBtn: document.getElementById("validateBtn"),
  preview: document.getElementById("jsonPreview"),
  previewStatus: document.getElementById("previewStatus"),
  quickStatus: document.getElementById("quickStatus"),
  editorStatus: document.getElementById("editorStatus"),
  modeAi: document.getElementById("modeAi"),
  modeTemplate: document.getElementById("modeTemplate"),
  generateBtn: document.getElementById("generateBtn"),
  aiSettings: document.getElementById("aiSettings"),
  advancedToggle: document.getElementById("advancedToggle"),
  advancedEditors: document.getElementById("advancedEditors"),
  simpleExtensions: document.getElementById("simpleExtensions"),
  extensionsJson: document.getElementById("extensionsJson"),
  characterBookJson: document.getElementById("characterBookJson"),
  platformSelect: document.getElementById("platformSelect"),
  platformHint: document.getElementById("platformHint")
};

const fields = {
  name: document.getElementById("name"),
  creator: document.getElementById("creator"),
  version: document.getElementById("version"),
  avatar: document.getElementById("avatar"),
  tags: document.getElementById("tags"),
  altGreetings: document.getElementById("altGreetings"),
  description: document.getElementById("description"),
  personality: document.getElementById("personality"),
  scenario: document.getElementById("scenario"),
  firstMes: document.getElementById("firstMes"),
  mesExample: document.getElementById("mesExample"),
  creatorNotes: document.getElementById("creatorNotes"),
  systemPrompt: document.getElementById("systemPrompt"),
  postHistory: document.getElementById("postHistory"),
  depthRole: document.getElementById("depthRole"),
  depthValue: document.getElementById("depthValue"),
  depthPrompt: document.getElementById("depthPrompt")
};

const quick = {
  name: document.getElementById("quickName"),
  concept: document.getElementById("quickConcept"),
  role: document.getElementById("quickRole"),
  relation: document.getElementById("quickRelation"),
  world: document.getElementById("quickWorld"),
  style: document.getElementById("quickStyle"),
  boundaries: document.getElementById("quickBoundaries"),
  lang: document.getElementById("quickLang"),
  apiBase: document.getElementById("apiBase"),
  apiKey: document.getElementById("apiKey"),
  apiModel: document.getElementById("apiModel"),
  apiTemp: document.getElementById("apiTemp")
};

const PLATFORM_PROFILES = {
  chub: {
    label: "CharHub / Chub (chara_card_v2)",
    exportMode: "v2",
    description: "保留 v2 全量字段，重点检查 chub 扩展对象。",
    validate(card, warnings) {
      const chub = card?.data?.extensions?.chub;
      if (chub && !isObject(chub)) {
        warnings.push("extensions.chub 必须是对象");
      }
      if (isObject(chub) && chub.full_path && typeof chub.full_path !== "string") {
        warnings.push("extensions.chub.full_path 必须是字符串");
      }
    }
  },
  sillytavern: {
    label: "SillyTavern (chara_card_v2)",
    exportMode: "v2",
    description: "检查 depth_prompt 与 character_book 是否符合 ST 预期。",
    validate(card, warnings) {
      validateDepthPrompt(card?.data?.extensions, warnings);
      validateCharacterBook(card?.data?.character_book, warnings);
    }
  },
  tavern_v1: {
    label: "Legacy Tavern v1",
    exportMode: "legacy_v1",
    description: "导出平铺字段，适配仅支持旧版 v1 的平台。",
    validate(card, warnings) {
      const out = convertToLegacyTavern(card);
      if (!out.name) {
        warnings.push("Legacy v1: name 不能为空");
      }
      if (!out.description) {
        warnings.push("Legacy v1: description 为空");
      }
      if (!out.first_mes) {
        warnings.push("Legacy v1: first_mes 为空");
      }
      if (!out.mes_example) {
        warnings.push("Legacy v1: mes_example 为空");
      }
    }
  }
};

function setStatus(el, message, isError = false) {
  if (!el) return;
  el.textContent = message;
  el.style.color = isError ? "#b43c18" : "#c95d2e";
}

function isObject(value) {
  return value && typeof value === "object" && !Array.isArray(value);
}

function getPlatformProfile(platformKey) {
  return PLATFORM_PROFILES[platformKey] || PLATFORM_PROFILES.chub;
}

function parseList(value) {
  return value
    .split(/[，,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function listToText(list) {
  return (list || []).join(", ");
}

function linesToList(text) {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function listToLines(list) {
  return (list || []).join("\n");
}

function clearExtras() {
  extraRoot = {};
  extraData = {};
}

function captureExtras(card) {
  const { spec, spec_version, data, ...rest } = card || {};
  extraRoot = rest || {};
  extraData = {};

  if (data && typeof data === "object") {
    Object.keys(data).forEach((key) => {
      if (!knownDataKeys.has(key)) {
        extraData[key] = data[key];
      }
    });
  }
}

function applyCardToForm(card) {
  const data = card?.data || {};
  fields.name.value = data.name || "";
  fields.creator.value = data.creator || "";
  fields.version.value = data.character_version || "";
  fields.avatar.value = data.avatar || "";
  fields.tags.value = listToText(data.tags || []);
  fields.altGreetings.value = listToLines(data.alternate_greetings || []);
  fields.description.value = data.description || "";
  fields.personality.value = data.personality || "";
  fields.scenario.value = data.scenario || "";
  fields.firstMes.value = data.first_mes || "";
  fields.mesExample.value = data.mes_example || "";
  fields.creatorNotes.value = data.creator_notes || "";
  fields.systemPrompt.value = data.system_prompt || "";
  fields.postHistory.value = data.post_history_instructions || "";

  stateExtensions = data.extensions && typeof data.extensions === "object" ? structuredClone(data.extensions) : {};
  const depthPrompt = stateExtensions?.depth_prompt || {};
  fields.depthRole.value = depthPrompt.role || "";
  fields.depthValue.value = depthPrompt.depth ?? "";
  fields.depthPrompt.value = depthPrompt.prompt || "";

  stateCharacterBook = data.character_book && typeof data.character_book === "object"
    ? structuredClone(data.character_book)
    : structuredClone(DEFAULT_CARD.data.character_book);

  ui.extensionsJson.value = JSON.stringify(stateExtensions || {}, null, 2);
  ui.characterBookJson.value = JSON.stringify(stateCharacterBook || {}, null, 2);
}

function buildExtensions() {
  if (ui.advancedToggle.checked) {
    const text = ui.extensionsJson.value.trim();
    if (!text) {
      stateExtensions = {};
      return {};
    }
    const parsed = JSON.parse(text);
    stateExtensions = parsed;
    return parsed;
  }

  const ext = structuredClone(stateExtensions || {});
  const role = fields.depthRole.value.trim();
  const depthRaw = fields.depthValue.value;
  const depth = depthRaw === "" ? null : Number(depthRaw);
  const prompt = fields.depthPrompt.value.trim();

  if (role || depth !== null || prompt) {
    ext.depth_prompt = {
      role: role || "system",
      depth: Number.isFinite(depth) ? depth : 4,
      prompt: prompt || ""
    };
  } else {
    delete ext.depth_prompt;
  }

  return ext;
}

function buildCharacterBook() {
  if (ui.advancedToggle.checked) {
    const text = ui.characterBookJson.value.trim();
    if (!text) {
      stateCharacterBook = structuredClone(DEFAULT_CARD.data.character_book);
      return stateCharacterBook;
    }
    const parsed = JSON.parse(text);
    stateCharacterBook = parsed;
    return parsed;
  }

  return stateCharacterBook || structuredClone(DEFAULT_CARD.data.character_book);
}

function buildCardFromForm() {
  const card = {
    spec: "chara_card_v2",
    spec_version: "2.0",
    ...extraRoot,
    data: {
      ...extraData,
      name: fields.name.value.trim(),
      description: fields.description.value,
      personality: fields.personality.value,
      first_mes: fields.firstMes.value,
      avatar: fields.avatar.value.trim(),
      mes_example: fields.mesExample.value,
      scenario: fields.scenario.value,
      creator_notes: fields.creatorNotes.value,
      system_prompt: fields.systemPrompt.value,
      post_history_instructions: fields.postHistory.value,
      alternate_greetings: linesToList(fields.altGreetings.value),
      tags: parseList(fields.tags.value),
      creator: fields.creator.value.trim(),
      character_version: fields.version.value.trim(),
      extensions: buildExtensions(),
      character_book: buildCharacterBook()
    }
  };
  return card;
}

function convertToLegacyTavern(card) {
  const data = card?.data || {};
  return {
    name: data.name || "",
    description: data.description || "",
    personality: data.personality || "",
    scenario: data.scenario || "",
    first_mes: data.first_mes || "",
    mes_example: data.mes_example || "",
    creatorcomment: data.creator_notes || "",
    avatar: data.avatar || "",
    tags: Array.isArray(data.tags) ? data.tags : []
  };
}

function convertLegacyToV2(legacy) {
  const card = structuredClone(DEFAULT_CARD);
  card.data.name = legacy?.name || "";
  card.data.description = legacy?.description || "";
  card.data.personality = legacy?.personality || "";
  card.data.scenario = legacy?.scenario || "";
  card.data.first_mes = legacy?.first_mes || legacy?.first_message || "";
  card.data.mes_example = legacy?.mes_example || legacy?.example_dialogue || "";
  card.data.creator_notes = legacy?.creatorcomment || "";
  card.data.avatar = legacy?.avatar || "";
  card.data.tags = Array.isArray(legacy?.tags) ? legacy.tags : [];
  return card;
}

function transformForPlatform(card, platformKey) {
  const profile = getPlatformProfile(platformKey);
  if (profile.exportMode === "legacy_v1") {
    return convertToLegacyTavern(card);
  }
  return card;
}

function inferPlatformFromCard(card, source) {
  if (source === "legacy") {
    return "tavern_v1";
  }
  if (card?.data?.extensions?.chub) {
    return "chub";
  }
  return "sillytavern";
}

function getOutputCardFromForm() {
  const card = buildCardFromForm();
  return transformForPlatform(card, selectedPlatform);
}

function updatePreview() {
  try {
    const out = getOutputCardFromForm();
    const profile = getPlatformProfile(selectedPlatform);
    ui.preview.textContent = JSON.stringify(out, null, 2);
    setStatus(ui.previewStatus, `预览已更新（${profile.label}）`);
  } catch (err) {
    setStatus(ui.previewStatus, `预览失败：${err.message}`, true);
  }
}

function validateBaseV2(card) {
  const warnings = [];
  if (!card?.spec || card.spec !== "chara_card_v2") {
    warnings.push("spec 需为 chara_card_v2");
  }
  if (card?.spec_version !== "2.0") {
    warnings.push("spec_version 建议固定为 2.0");
  }
  if (!card?.data?.name) {
    warnings.push("name 不能为空");
  }
  if (!card?.data?.description) {
    warnings.push("description 为空，建议补充");
  }
  if (!card?.data?.first_mes) {
    warnings.push("first_mes 为空，建议补充");
  }
  if (!Array.isArray(card?.data?.alternate_greetings)) {
    warnings.push("alternate_greetings 应为数组");
  }
  if (!Array.isArray(card?.data?.tags)) {
    warnings.push("tags 应为数组");
  }
  return warnings;
}

function validateDepthPrompt(extensions, warnings) {
  if (!isObject(extensions)) {
    return;
  }
  const depth = extensions.depth_prompt;
  if (depth == null) {
    return;
  }
  if (!isObject(depth)) {
    warnings.push("extensions.depth_prompt 必须是对象");
    return;
  }
  if (depth.role != null && typeof depth.role !== "string") {
    warnings.push("extensions.depth_prompt.role 必须是字符串");
  }
  if (depth.depth != null && !Number.isFinite(Number(depth.depth))) {
    warnings.push("extensions.depth_prompt.depth 必须是数字");
  }
  if (depth.prompt != null && typeof depth.prompt !== "string") {
    warnings.push("extensions.depth_prompt.prompt 必须是字符串");
  }
}

function validateCharacterBook(book, warnings) {
  if (book == null) {
    return;
  }
  if (!isObject(book)) {
    warnings.push("character_book 必须是对象");
    return;
  }
  if (book.entries != null && !Array.isArray(book.entries)) {
    warnings.push("character_book.entries 必须是数组");
  }
  if (book.scan_depth != null && !Number.isFinite(Number(book.scan_depth))) {
    warnings.push("character_book.scan_depth 必须是数字");
  }
  if (book.token_budget != null && !Number.isFinite(Number(book.token_budget))) {
    warnings.push("character_book.token_budget 必须是数字");
  }
}

function validateCardForPlatform(card, platformKey) {
  const warnings = validateBaseV2(card);
  const profile = getPlatformProfile(platformKey);
  profile.validate(card, warnings);
  return warnings;
}

function downloadJson() {
  try {
    const out = getOutputCardFromForm();
    const blob = new Blob([JSON.stringify(out, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const fileNameBase = out?.data?.name || out?.name || "character";
    const suffix = selectedPlatform === "tavern_v1" ? "_tavern_v1" : "_chara_card_v2";
    link.href = url;
    link.download = `${fileNameBase}${suffix}.json`;
    link.click();
    URL.revokeObjectURL(url);
    setStatus(ui.editorStatus, "已导出 JSON");
  } catch (err) {
    setStatus(ui.editorStatus, `导出失败：${err.message}`, true);
  }
}

async function copyJson() {
  try {
    const out = getOutputCardFromForm();
    const text = JSON.stringify(out, null, 2);
    await navigator.clipboard.writeText(text);
    setStatus(ui.editorStatus, "JSON 已复制");
  } catch (err) {
    setStatus(ui.editorStatus, `复制失败：${err.message}`, true);
  }
}

function parseJsonFromText(text) {
  const trimmed = text.trim();
  if (!trimmed) return null;
  try {
    return JSON.parse(trimmed);
  } catch (_) {
    const cleaned = trimmed
      .replace(/```json/g, "")
      .replace(/```/g, "")
      .trim();
    const start = cleaned.indexOf("{");
    const end = cleaned.lastIndexOf("}");
    if (start >= 0 && end > start) {
      return JSON.parse(cleaned.slice(start, end + 1));
    }
    throw new Error("无法解析 JSON 输出");
  }
}

function normalizeImportedPayload(payload) {
  if (payload?.spec === "chara_card_v2" && isObject(payload?.data)) {
    return { source: "v2", card: payload };
  }

  if (isObject(payload?.data) && (payload.data.name || payload.data.first_mes || payload.data.description)) {
    return {
      source: "v2",
      card: {
        spec: "chara_card_v2",
        spec_version: payload.spec_version || "2.0",
        data: payload.data
      }
    };
  }

  if (isObject(payload) && (payload.name || payload.first_mes || payload.description)) {
    return { source: "legacy", card: convertLegacyToV2(payload) };
  }

  throw new Error("不支持的 JSON 格式：需要 chara_card_v2 或 legacy v1");
}

function fillQuickDefaults() {
  if (!quick.lang.value) quick.lang.value = "中文";
}

function buildTemplateCard(input) {
  const name = input.name || "未命名角色";
  const concept = input.concept || "【请补充核心设定】";
  const role = input.role || "【请补充身份】";
  const relation = input.relation || "【请补充与 {{user}} 的关系】";
  const world = input.world || "【请补充世界观/场景】";
  const style = input.style || "【请补充叙事风格】";
  const boundaries = input.boundaries || "【请补充内容边界】";
  const language = input.lang || "中文";

  const description = `### Overview\n${concept}\n\n### Identity\n- ${role}\n- 世界观：${world}\n\n### Relationship to {{user}}\n- ${relation}\n\n### Personality\n- 标签：${style}\n- 喜好：【请补充】\n- 讨厌：【请补充】\n- 目标：【请补充】\n\n### Behavior and Habits\n- 【请补充】\n\n### Speech\n- 语言：${language}\n- 风格：${style}\n\n### Boundaries\n- ${boundaries}`;

  const firstMes = `${name}注意到了{{user}}，却迟迟说不出口。\n\n"……" 她/他/他们停顿了一下，努力组织语言。\n\n（你可以继续由此展开第一段对话。）`;

  const mesExample = `<START>\n[context: ${world}]\n\n{{char}}：${name}深吸一口气，试着把话说清楚。\n{{user}}：\n`;

  const card = structuredClone(DEFAULT_CARD);
  card.data.name = name;
  card.data.description = description;
  card.data.first_mes = firstMes;
  card.data.mes_example = mesExample;
  card.data.scenario = world;
  card.data.tags = ["template", "chara_card_v2"];
  return card;
}

function buildAiPrompt(input) {
  const profile = getPlatformProfile(selectedPlatform);
  return `请根据以下要点生成一张完整的角色卡（chara_card_v2, spec_version=2.0），只输出 JSON，不要代码块。\n\n【目标平台】\n- ${profile.label}\n- 说明：${profile.description}\n\n【关键信息】\n- 角色名：${input.name || "未命名角色"}\n- 一句话设定：${input.concept || ""}\n- 身份/关键词：${input.role || ""}\n- 与 {{user}} 的关系/动机：${input.relation || ""}\n- 世界观/场景：${input.world || ""}\n- 语言/风格：${input.style || ""}\n- 边界/尺度：${input.boundaries || ""}\n- 输出语言：${input.lang || "中文"}\n\n【格式要求】\n- 顶层字段：spec, spec_version, data\n- spec 固定为 "chara_card_v2"，spec_version 固定为 "2.0"\n- data 字段至少包含：name, description, first_mes, mes_example, scenario, tags, creator_notes, system_prompt, post_history_instructions, alternate_greetings\n- description 建议使用 Markdown 小节（Overview/Appearance/Origin/Personality/Behavior 等）\n- 允许使用 {{user}} 与 {{char}} 占位符\n- 若有 NSFW 或禁忌内容，放入 description 与 creator_notes 说明\n`;
}

async function callAi(input) {
  const base = input.apiBase?.trim();
  const key = input.apiKey?.trim();
  const model = input.apiModel?.trim();
  const temperature = Number(input.apiTemp || 0.8);

  if (!base || !model) {
    throw new Error("请填写 API Base URL 和模型名称");
  }

  const systemPrompt = "你是角色卡作者，只输出符合格式的 JSON。";
  const userPrompt = buildAiPrompt(input);

  const url = base.replace(/\/$/, "") + "/v1/chat/completions";
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(key ? { Authorization: `Bearer ${key}` } : {})
    },
    body: JSON.stringify({
      model,
      temperature,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt }
      ]
    })
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API 请求失败：${response.status} ${text}`);
  }

  const data = await response.json();
  const message = data?.choices?.[0]?.message?.content || "";
  const parsed = parseJsonFromText(message);
  if (!parsed) {
    throw new Error("未获取到有效 JSON");
  }
  return parsed;
}

function loadCardEnvelope(envelope, options = {}) {
  const card = envelope.card;
  if (envelope.source === "v2") {
    captureExtras(card);
  } else {
    clearExtras();
  }

  applyCardToForm(card);

  if (options.syncPlatform) {
    setPlatform(inferPlatformFromCard(card, envelope.source));
  }

  updatePreview();
}

function handleImport(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const parsed = JSON.parse(reader.result);
      const normalized = normalizeImportedPayload(parsed);
      loadCardEnvelope(normalized, { syncPlatform: true });
      setStatus(ui.editorStatus, "已导入角色卡");
    } catch (err) {
      setStatus(ui.editorStatus, `导入失败：${err.message}`, true);
    }
  };
  reader.readAsText(file, "utf-8");
}

function getQuickInput() {
  return {
    name: quick.name.value.trim(),
    concept: quick.concept.value.trim(),
    role: quick.role.value.trim(),
    relation: quick.relation.value.trim(),
    world: quick.world.value.trim(),
    style: quick.style.value.trim(),
    boundaries: quick.boundaries.value.trim(),
    lang: quick.lang.value.trim(),
    apiBase: quick.apiBase.value.trim(),
    apiKey: quick.apiKey.value.trim(),
    apiModel: quick.apiModel.value.trim(),
    apiTemp: quick.apiTemp.value
  };
}

async function handleGenerate() {
  fillQuickDefaults();
  const input = getQuickInput();
  setStatus(ui.quickStatus, "生成中，请稍候...");

  try {
    let output = null;
    if (aiMode === "ai") {
      try {
        output = await callAi(input);
      } catch (err) {
        output = buildTemplateCard(input);
        setStatus(ui.quickStatus, `AI 失败，已回退模板：${err.message}`, true);
      }
    } else {
      output = buildTemplateCard(input);
    }

    const normalized = normalizeImportedPayload(output);
    loadCardEnvelope(normalized, { syncPlatform: false });
    setStatus(ui.quickStatus, "生成完成，已载入编辑区");
  } catch (err) {
    setStatus(ui.quickStatus, `生成失败：${err.message}`, true);
  }
}

function toggleAdvanced() {
  const advanced = ui.advancedToggle.checked;
  ui.advancedEditors.classList.toggle("hidden", !advanced);
  ui.simpleExtensions.classList.toggle("hidden", advanced);
  if (advanced) {
    ui.extensionsJson.value = JSON.stringify(stateExtensions || {}, null, 2);
    ui.characterBookJson.value = JSON.stringify(stateCharacterBook || {}, null, 2);
  } else {
    try {
      const ext = ui.extensionsJson.value.trim();
      if (ext) {
        stateExtensions = JSON.parse(ext);
      }
      const book = ui.characterBookJson.value.trim();
      if (book) {
        stateCharacterBook = JSON.parse(book);
      }
      const depthPrompt = stateExtensions?.depth_prompt || {};
      fields.depthRole.value = depthPrompt.role || "";
      fields.depthValue.value = depthPrompt.depth ?? "";
      fields.depthPrompt.value = depthPrompt.prompt || "";
    } catch (err) {
      setStatus(ui.editorStatus, `高级 JSON 解析失败：${err.message}`, true);
    }
  }
}

function setAiMode(mode) {
  aiMode = mode;
  ui.modeAi.classList.toggle("active", mode === "ai");
  ui.modeTemplate.classList.toggle("active", mode === "template");
  ui.aiSettings.style.display = mode === "ai" ? "block" : "none";
}

function setPlatform(platformKey) {
  const profile = getPlatformProfile(platformKey);
  selectedPlatform = PLATFORM_PROFILES[platformKey] ? platformKey : "chub";
  ui.platformSelect.value = selectedPlatform;
  ui.platformHint.textContent = profile.description;
}

function debounce(fn, delay = 300) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

ui.importBtn.addEventListener("click", () => ui.fileInput.click());
ui.fileInput.addEventListener("change", (event) => {
  const file = event.target.files?.[0];
  if (file) handleImport(file);
});

ui.exportBtn.addEventListener("click", downloadJson);
ui.copyBtn.addEventListener("click", copyJson);
ui.refreshPreview.addEventListener("click", updatePreview);
ui.validateBtn.addEventListener("click", () => {
  try {
    const card = buildCardFromForm();
    const warnings = validateCardForPlatform(card, selectedPlatform);
    const profile = getPlatformProfile(selectedPlatform);
    if (warnings.length === 0) {
      setStatus(ui.previewStatus, `校验通过（${profile.label}）`);
    } else {
      setStatus(ui.previewStatus, `校验提示（${profile.label}）：${warnings.join("；")}`, true);
    }
  } catch (err) {
    setStatus(ui.previewStatus, `校验失败：${err.message}`, true);
  }
});

ui.generateBtn.addEventListener("click", handleGenerate);
ui.modeAi.addEventListener("click", () => setAiMode("ai"));
ui.modeTemplate.addEventListener("click", () => setAiMode("template"));
ui.advancedToggle.addEventListener("change", toggleAdvanced);
ui.platformSelect.addEventListener("change", () => {
  setPlatform(ui.platformSelect.value);
  updatePreview();
});

window.addEventListener("load", () => {
  setAiMode("ai");
  setPlatform("chub");
  loadCardEnvelope({ source: "v2", card: structuredClone(DEFAULT_CARD) }, { syncPlatform: false });
  const onInput = debounce(updatePreview, 400);
  document.querySelectorAll("input, textarea, select").forEach((el) => {
    if (el.id === "fileInput") return;
    el.addEventListener("input", onInput);
  });
});
