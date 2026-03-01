<template>
  <div class="flex-row editor-layout">
    <div class="sidebar">
      <div class="panel-card">
        <div class="panel-title">工作区与方言</div>
        <div class="flex-column">
          <a-select
            v-model:value="selectedWorkspaceId"
            placeholder="选择工作区"
            :loading="workspaceStore.loading"
            @change="handleWorkspaceChange"
          >
            <a-select-option v-for="item in workspaceStore.items" :key="item.id" :value="item.id">
              {{ item.name }}
            </a-select-option>
          </a-select>
          <div class="button-row">
            <a-button type="primary" @click="openWorkspaceModal()">新建工作区</a-button>
            <a-button :disabled="!selectedWorkspace" @click="openWorkspaceModal(selectedWorkspace)">
              编辑
            </a-button>
            <a-button danger :disabled="!selectedWorkspace" @click="removeWorkspace">
              删除
            </a-button>
          </div>
          <a-select
            v-model:value="selectedDialect"
            placeholder="选择SQL方言"
            :loading="dialectLoading"
            @change="saveDialect"
          >
            <a-select-option v-for="dialect in dialects" :key="dialect.code" :value="dialect.code">
              {{ dialect.label }}
            </a-select-option>
          </a-select>
        </div>
      </div>
      <div class="panel-card">
        <div class="panel-title">表清单</div>
        <div class="flex-column">
          <a-input v-model:value="tableName" placeholder="输入表名" />
          <a-button type="primary" :loading="catalogStore.loading" @click="addTable">
            添加表
          </a-button>
          <a-list
            size="small"
            :data-source="tableItems"
            :locale="{ emptyText: '暂无表记录' }"
            bordered
          >
            <template #renderItem="{ item }">
              <a-list-item>{{ item.value }}</a-list-item>
            </template>
          </a-list>
        </div>
      </div>
    </div>
    <div class="content">
      <SqlEditor />
      <ErrorList />
    </div>
    <a-modal
      v-model:open="workspaceModalVisible"
      title="工作区"
      :confirm-loading="workspaceSubmitting"
      @ok="submitWorkspace"
    >
      <a-form layout="vertical">
        <a-form-item label="名称">
          <a-input v-model:value="workspaceForm.name" />
        </a-form-item>
        <a-form-item label="方言">
          <a-select v-model:value="workspaceForm.dialect">
            <a-select-option v-for="dialect in dialects" :key="dialect.code" :value="dialect.code">
              {{ dialect.label }}
            </a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { message } from "ant-design-vue";

import SqlEditor from "../components/SqlEditor.vue";
import ErrorList from "../components/ErrorList.vue";
import { listDialects, type Dialect } from "../api/dialects";
import { useCatalogStore } from "../store/catalog";
import { useLspStore } from "../store/lsp";
import { useWorkspaceStore } from "../store/workspace";

const workspaceStore = useWorkspaceStore();
const catalogStore = useCatalogStore();
const lspStore = useLspStore();

const dialects = ref<Dialect[]>([]);
const dialectLoading = ref(false);
const selectedWorkspaceId = ref<number | null>(null);
const selectedDialect = ref<string>("");
const tableName = ref("");

const workspaceModalVisible = ref(false);
const workspaceSubmitting = ref(false);
const workspaceForm = reactive({
  id: null as number | null,
  name: "",
  dialect: "",
});

const selectedWorkspace = computed(() =>
  workspaceStore.items.find((item) => item.id === selectedWorkspaceId.value)
);

const tableItems = computed(() => catalogStore.items.filter((item) => item.category === "table"));

async function loadDialects() {
  dialectLoading.value = true;
  try {
    dialects.value = await listDialects();
  } finally {
    dialectLoading.value = false;
  }
}

function handleWorkspaceChange(value: number) {
  workspaceStore.setSelectedId(value);
  const workspace = workspaceStore.items.find((item) => item.id === value);
  if (workspace) {
    selectedDialect.value = workspace.dialect;
    lspStore.setDialect(workspace.dialect);
  }
}

async function openWorkspaceModal(workspace?: { id: number; name: string; dialect: string }) {
  if (workspace) {
    workspaceForm.id = workspace.id;
    workspaceForm.name = workspace.name;
    workspaceForm.dialect = workspace.dialect;
  } else {
    workspaceForm.id = null;
    workspaceForm.name = "";
    workspaceForm.dialect = selectedDialect.value || dialects.value[0]?.code || "";
  }
  workspaceModalVisible.value = true;
}

async function submitWorkspace() {
  if (!workspaceForm.name || !workspaceForm.dialect) {
    message.error("请填写工作区名称与方言");
    return;
  }
  workspaceSubmitting.value = true;
  try {
    if (workspaceForm.id) {
      const updated = await workspaceStore.editWorkspace(workspaceForm.id, {
        name: workspaceForm.name,
        dialect: workspaceForm.dialect,
      });
      selectedWorkspaceId.value = updated.id;
      selectedDialect.value = updated.dialect;
      lspStore.setDialect(updated.dialect);
      message.success("工作区已更新");
    } else {
      const created = await workspaceStore.addWorkspace({
        name: workspaceForm.name,
        dialect: workspaceForm.dialect,
      });
      selectedWorkspaceId.value = created.id;
      selectedDialect.value = created.dialect;
      lspStore.setDialect(created.dialect);
      message.success("工作区已创建");
    }
    workspaceModalVisible.value = false;
  } finally {
    workspaceSubmitting.value = false;
  }
}

async function removeWorkspace() {
  if (!selectedWorkspace.value) return;
  await workspaceStore.removeWorkspace(selectedWorkspace.value.id);
  message.success("工作区已删除");
}

async function saveDialect() {
  if (!selectedWorkspace.value || !selectedDialect.value) return;
  await workspaceStore.editWorkspace(selectedWorkspace.value.id, {
    name: selectedWorkspace.value.name,
    dialect: selectedDialect.value,
  });
  lspStore.setDialect(selectedDialect.value);
  message.success("方言已更新");
}

async function addTable() {
  if (!tableName.value || !selectedDialect.value) {
    message.error("请填写表名");
    return;
  }
  await catalogStore.addTable({
    value: tableName.value,
    dialect: selectedDialect.value,
    workspace_id: selectedWorkspaceId.value ?? undefined,
  });
  tableName.value = "";
  message.success("表已添加");
}

watch(
  () => [selectedDialect.value, selectedWorkspaceId.value],
  async ([dialect, workspaceId]) => {
    if (dialect) {
      await catalogStore.fetchAll(dialect, workspaceId);
    }
  }
);

onMounted(async () => {
  await loadDialects();
  await workspaceStore.fetchAll();
  selectedWorkspaceId.value = workspaceStore.selectedId;
  const initialDialect =
    workspaceStore.items.find((item) => item.id === selectedWorkspaceId.value)?.dialect ||
    dialects.value[0]?.code ||
    "";
  if (initialDialect) {
    selectedDialect.value = initialDialect;
    lspStore.setDialect(initialDialect);
    await catalogStore.fetchAll(initialDialect, selectedWorkspaceId.value);
  }
});
</script>

<style scoped lang="scss">
.editor-layout {
  align-items: flex-start;
}

.sidebar {
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.button-row {
  display: flex;
  gap: 8px;
}
</style>
