#!/usr/bin/env bash
set -euo pipefail

# K1 SAM3D Environment Pipeline Orchestrator
# Usage: ./run_k1_environment_pipeline.sh [env_name]

ENV_NAME="${1:-battlestation_batman}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Use venv Python if available, otherwise system Python
if [[ -f "${SCRIPT_DIR}/.venv/bin/python" ]]; then
    PYTHON="${SCRIPT_DIR}/.venv/bin/python"
    echo "[INFO] Using venv Python: ${PYTHON}"
else
    PYTHON="python3"
    echo "[INFO] Using system Python: ${PYTHON}"
fi

echo "=============================================="
echo "K1 Environment Pipeline: ${ENV_NAME}"
echo "=============================================="

echo ""
echo "[1/4] Normalising reference image..."
"${PYTHON}" "${SCRIPT_DIR}/scripts/prep_for_sam3d.py" "${ENV_NAME}"

echo ""
echo "[2/4] Running SAM3 segmentation..."
if [[ "${ENV_NAME}" == "battlestation_batman" ]]; then
    "${PYTHON}" "${SCRIPT_DIR}/scripts/sam3_segment.py" "${ENV_NAME}" \
        --prompts "gaming chair" "desk surface" "monitor" "pc tower" "keyboard"
elif [[ "${ENV_NAME}" == "moody_laptop_desk" ]]; then
    "${PYTHON}" "${SCRIPT_DIR}/scripts/sam3_segment.py" "${ENV_NAME}" \
        --prompts "laptop" "desk surface" "lamp" "mug" "background"
else
    echo "[WARN] Unknown environment, using generic prompts"
    "${PYTHON}" "${SCRIPT_DIR}/scripts/sam3_segment.py" "${ENV_NAME}" \
        --prompts "desk" "computer" "chair" "lamp"
fi

echo ""
echo "[3/4] Running SAM3D reconstruction..."
if [[ "${ENV_NAME}" == "battlestation_batman" ]]; then
    "${PYTHON}" "${SCRIPT_DIR}/scripts/sam3d_reconstruct.py" "${ENV_NAME}" \
        --objects gaming_chair desk_surface monitor pc_tower keyboard
elif [[ "${ENV_NAME}" == "moody_laptop_desk" ]]; then
    "${PYTHON}" "${SCRIPT_DIR}/scripts/sam3d_reconstruct.py" "${ENV_NAME}" \
        --objects laptop desk_surface lamp mug background
else
    "${PYTHON}" "${SCRIPT_DIR}/scripts/sam3d_reconstruct.py" "${ENV_NAME}" \
        --objects desk computer chair lamp
fi

echo ""
echo "[4/4] Ready for Blender!"
echo ""
echo "=============================================="
echo "NEXT STEPS (in BlenderMCP):"
echo "=============================================="
echo ""
echo "1. Run K1 Master Build:"
echo "   exec(open('../03_Scripts_MCP/K1_MASTER_BUILD.py').read())"
echo ""
echo "2. Run environment build:"
if [[ "${ENV_NAME}" == "battlestation_batman" ]]; then
    echo "   exec(open('scripts/build_battlestation_batman.py').read())"
elif [[ "${ENV_NAME}" == "moody_laptop_desk" ]]; then
    echo "   exec(open('scripts/build_moody_laptop_desk.py').read())"
else
    echo "   exec(open('scripts/build_${ENV_NAME}.py').read())"
fi
echo ""
echo "3. Render to: renders/${ENV_NAME}/hero_1080p.png"
echo "=============================================="
