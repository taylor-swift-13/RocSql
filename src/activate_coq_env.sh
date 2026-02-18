#!/bin/bash
# Coq 环境激活脚本
# 使用方法: source activate_coq_env.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
export PROJECT_DIR

# 可选：按需启用代理（如果已设置则保持）
if [ -n "${http_proxy:-}" ]; then
  export http_proxy
fi
if [ -n "${https_proxy:-}" ]; then
  export https_proxy
fi

# 激活 opam 环境（优先 coqswitch，其次当前 switch）
if command -v opam >/dev/null 2>&1; then
  if opam switch list --short 2>/dev/null | grep -qx "coqswitch"; then
    eval "$(opam env --switch=coqswitch)"
  else
    eval "$(opam env)"
  fi
fi

if [ -d "$WORKSPACE_DIR/CoqStoq" ]; then
  export COQSTOQ_PATH="$WORKSPACE_DIR/CoqStoq"
fi
export PYTHONPATH="$PROJECT_DIR:${PYTHONPATH:-}"

echo "=========================================="
echo "Coq 环境已激活"
echo "=========================================="
echo "Coq 版本: $(coqc --version 2>/dev/null | head -1 || echo 'coqc 未找到')"
echo "coq-lsp 版本: $(coq-lsp --version 2>/dev/null || echo 'N/A')"
echo "Opam switch: $(opam switch show 2>/dev/null || echo 'N/A')"
echo ""
echo "项目目录: $PROJECT_DIR"
echo "CoqStoq 路径: ${COQSTOQ_PATH:-未设置}"
echo ""
echo "可用命令:"
echo "  cd $PROJECT_DIR          # 进入项目目录"
echo "  python verify_demo.py            # 运行验证示例"
echo "  python verify.py test:39 'Proof. ... Qed.'"
echo "=========================================="
