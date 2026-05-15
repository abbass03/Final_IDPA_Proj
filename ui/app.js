const state = {
    options: null,
    result: null,
    activeArtifact: "tree1_json",
};

const elements = {
    modeSelect: document.getElementById("modeSelect"),
    methodSelect: document.getElementById("methodSelect"),
    file1Select: document.getElementById("file1Select"),
    file2Select: document.getElementById("file2Select"),
    compareButton: document.getElementById("compareButton"),
    swapButton: document.getElementById("swapButton"),
    statusPill: document.getElementById("statusPill"),
    distanceValue: document.getElementById("distanceValue"),
    similarityValue: document.getElementById("similarityValue"),
    patchValue: document.getElementById("patchValue"),
    opsValue: document.getElementById("opsValue"),
    tree1Nodes: document.getElementById("tree1Nodes"),
    tree2Nodes: document.getElementById("tree2Nodes"),
    insertCount: document.getElementById("insertCount"),
    deleteCount: document.getElementById("deleteCount"),
    updateCount: document.getElementById("updateCount"),
    reportView: document.getElementById("reportView"),
    sourcePreview: document.getElementById("sourcePreview"),
    targetPreview: document.getElementById("targetPreview"),
    operationsList: document.getElementById("operationsList"),
    opsSubtitle: document.getElementById("opsSubtitle"),
    tree1View: document.getElementById("tree1View"),
    tree2View: document.getElementById("tree2View"),
    patchedTreeView: document.getElementById("patchedTreeView"),
    artifactView: document.getElementById("artifactView"),
};

function setStatus(label, kind) {
    elements.statusPill.textContent = label;
    elements.statusPill.className = `status-pill ${kind}`;
}

function fillSelect(select, values) {
    select.innerHTML = "";
    values.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
    });
}

async function fetchTextPreview(relativePath) {
    if (!relativePath) {
        return "No file selected.";
    }
    const response = await fetch(`/api/file?path=${encodeURIComponent(relativePath)}`);
    if (!response.ok) {
        return "Could not load file preview.";
    }
    return response.text();
}

async function refreshPreviews() {
    const [source, target] = await Promise.all([
        fetchTextPreview(elements.file1Select.value),
        fetchTextPreview(elements.file2Select.value),
    ]);

    elements.sourcePreview.textContent = source;
    elements.targetPreview.textContent = target;
    elements.sourcePreview.classList.remove("empty-state");
    elements.targetPreview.classList.remove("empty-state");
}

function updateFileChoices() {
    const mode = elements.modeSelect.value;
    const files = state.options.modes[mode].files;
    fillSelect(elements.file1Select, files);
    fillSelect(elements.file2Select, files);

    if (files.length > 1) {
        elements.file2Select.selectedIndex = 1;
    }

    refreshPreviews();
}

function renderTreeNode(node, depth = 0) {
    const container = document.createElement("div");
    container.className = "tree-node";
    container.style.marginLeft = `${depth * 10}px`;

    const line = document.createElement("div");
    const label = document.createElement("span");
    label.className = "tree-label";
    label.textContent = node.label;
    line.appendChild(label);

    const meta = document.createElement("span");
    meta.className = "tree-meta";
    meta.textContent = `[${node.node_type}]`;
    line.appendChild(meta);

    if (node.value !== null && node.value !== undefined) {
        const value = document.createElement("span");
        value.className = "tree-meta tree-value";
        value.textContent = ` = ${node.value}`;
        line.appendChild(value);
    }

    container.appendChild(line);

    (node.children || []).forEach((child) => {
        container.appendChild(renderTreeNode(child, depth + 1));
    });

    return container;
}

function renderOperations(ops) {
    elements.operationsList.innerHTML = "";

    if (!ops || ops.length === 0) {
        elements.operationsList.textContent = "No visible operations.";
        elements.operationsList.classList.add("empty-state");
        return;
    }

    elements.operationsList.classList.remove("empty-state");

    ops.forEach((op) => {
        const card = document.createElement("div");
        card.className = "operation-card";

        const header = document.createElement("div");
        header.className = "operation-header";

        const kind = document.createElement("div");
        kind.className = "op-kind";
        kind.textContent = op.op || "operation";

        const path = document.createElement("div");
        path.className = "op-path";
        path.textContent = op.path || op.source_ref || op.parent_ref || "";

        header.append(kind, path);
        card.appendChild(header);

        const details = [];
        if (op.old_label !== undefined || op.new_label !== undefined) {
            details.push(`label: ${op.old_label ?? "-"} -> ${op.new_label ?? "-"}`);
        }
        if (op.old_value !== undefined || op.new_value !== undefined) {
            details.push(`value: ${op.old_value ?? "-"} -> ${op.new_value ?? "-"}`);
        }
        if (op.position !== undefined && op.position !== null) {
            details.push(`position: ${op.position}`);
        }
        if (op.note) {
            details.push(`note: ${op.note}`);
        }

        const body = document.createElement("pre");
        body.className = "code-block";
        body.textContent = details.join("\n") || JSON.stringify(op, null, 2);
        card.appendChild(body);

        elements.operationsList.appendChild(card);
    });
}

function renderMetrics(result) {
    elements.distanceValue.textContent = result.stats.distance;
    elements.similarityValue.textContent = result.stats.similarity;
    elements.patchValue.textContent = result.patch.success ? "Valid" : "Mismatch";
    elements.opsValue.textContent = result.summary.total_visible;
    elements.tree1Nodes.textContent = result.stats.tree1_nodes;
    elements.tree2Nodes.textContent = result.stats.tree2_nodes;
    elements.insertCount.textContent = result.summary.insert;
    elements.deleteCount.textContent = result.summary.delete;
    elements.updateCount.textContent = result.summary.update;
}

function renderTrees(result) {
    elements.tree1View.innerHTML = "";
    elements.tree2View.innerHTML = "";
    elements.patchedTreeView.innerHTML = "";
    elements.tree1View.classList.remove("empty-state");
    elements.tree2View.classList.remove("empty-state");
    elements.patchedTreeView.classList.remove("empty-state");

    elements.tree1View.appendChild(renderTreeNode(result.trees.tree1));
    elements.tree2View.appendChild(renderTreeNode(result.trees.tree2));
    elements.patchedTreeView.appendChild(renderTreeNode(result.trees.patched));
}

function updateArtifactView() {
    if (!state.result) {
        elements.artifactView.textContent = "Run a comparison to inspect generated artifacts.";
        elements.artifactView.classList.add("empty-state");
        return;
    }

    const value = state.result.outputs[state.activeArtifact];
    elements.artifactView.textContent = value || "Artifact not available for this mode.";
    elements.artifactView.classList.remove("empty-state");
}

function renderResult(result) {
    state.result = result;
    renderMetrics(result);
    renderOperations(result.ops.visible);
    renderTrees(result);

    elements.reportView.textContent = result.outputs.report;
    elements.reportView.classList.remove("empty-state");
    elements.opsSubtitle.textContent = `${result.ops.visible.length} visible operations using ${result.method}.`;

    if (result.mode === "wiki") {
        state.activeArtifact = "tree1_infobox";
    } else if (!result.outputs[state.activeArtifact]) {
        state.activeArtifact = "tree1_json";
    }
    updateArtifactButtons();
    updateArtifactView();
}

function updateArtifactButtons() {
    document.querySelectorAll(".artifact-button").forEach((button) => {
        button.classList.toggle("active", button.dataset.artifact === state.activeArtifact);
    });
}

function activateTab(tabName) {
    document.querySelectorAll(".tab-button").forEach((button) => {
        button.classList.toggle("active", button.dataset.tab === tabName);
    });
    document.querySelectorAll(".tab-panel").forEach((panel) => {
        panel.classList.toggle("active", panel.id === `${tabName}Tab`);
    });
}

async function runComparison() {
    setStatus("Running", "loading");
    elements.compareButton.disabled = true;

    try {
        const response = await fetch("/api/compare", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mode: elements.modeSelect.value,
                method: elements.methodSelect.value,
                file1: elements.file1Select.value,
                file2: elements.file2Select.value,
            }),
        });

        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || "Comparison failed.");
        }

        renderResult(payload);
        setStatus("Comparison Complete", "success");
        activateTab("overview");
    } catch (error) {
        setStatus("Error", "error");
        elements.reportView.textContent = error.message;
        elements.reportView.classList.remove("empty-state");
    } finally {
        elements.compareButton.disabled = false;
    }
}

async function initialize() {
    setStatus("Loading Files", "loading");
    const response = await fetch("/api/options");
    state.options = await response.json();

    fillSelect(elements.modeSelect, Object.keys(state.options.modes));
    fillSelect(elements.methodSelect, state.options.methods);
    updateFileChoices();
    setStatus("Ready", "idle");
}

elements.modeSelect.addEventListener("change", updateFileChoices);
elements.file1Select.addEventListener("change", refreshPreviews);
elements.file2Select.addEventListener("change", refreshPreviews);
elements.compareButton.addEventListener("click", runComparison);
elements.swapButton.addEventListener("click", () => {
    const first = elements.file1Select.value;
    elements.file1Select.value = elements.file2Select.value;
    elements.file2Select.value = first;
    refreshPreviews();
});

document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => activateTab(button.dataset.tab));
});

document.querySelectorAll(".artifact-button").forEach((button) => {
    button.addEventListener("click", () => {
        state.activeArtifact = button.dataset.artifact;
        updateArtifactButtons();
        updateArtifactView();
    });
});

initialize();
