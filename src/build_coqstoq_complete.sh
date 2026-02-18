#!/bin/bash
# 完整的 CoqStoq 项目构建脚本（全量 clean + build + 验证）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COQSTOQ_DIR="$WORKSPACE_DIR/CoqStoq"

if command -v opam >/dev/null 2>&1; then
  if opam switch list --short 2>/dev/null | grep -qx "coqswitch"; then
    eval "$(opam env --switch=coqswitch)"
  else
    eval "$(opam env)"
  fi
fi

if [ ! -d "$COQSTOQ_DIR" ]; then
  echo "错误: 未找到 CoqStoq 目录: $COQSTOQ_DIR"
  exit 1
fi

cd "$COQSTOQ_DIR"
export PYTHONPATH="$COQSTOQ_DIR:$COQSTOQ_DIR/coqpyt:${PYTHONPATH:-}"
N_JOBS="${N_JOBS:-4}"

echo "=============================================="
echo "CoqStoq 完整项目构建"
echo "=============================================="
echo ""
echo "Coq 版本:"
coqc --version
echo ""

# compcert 的 configure 在部分环境中可能丢失可执行权限
if [ -f "test-repos/compcert/configure" ]; then
  chmod +x "test-repos/compcert/configure"
fi

# 清理旧文件
echo "=== 步骤 1: 清理旧构建文件 ==="
for dir in test-repos/* val-repos/* cutoff-repos/*; do
  if [ -d "$dir" ]; then
    (cd "$dir" && make clean 2>/dev/null || true)
    (cd "$dir" && find . -name "*.vo" -delete 2>/dev/null || true)
    (cd "$dir" && find . -name "*.glob" -delete 2>/dev/null || true)
  fi
done
echo "清理完成"
echo ""

# 构建所有项目
echo "=== 步骤 2: 构建所有项目 ==="
python3 -m coqstoq.build_projects --n_jobs "$N_JOBS" 2>&1 | tee /tmp/build_all.log

echo ""
echo "=============================================="
echo "构建完成！"
echo "查看日志: /tmp/build_all.log"
echo "=============================================="

# 生成状态报告
echo ""
echo "=== 构建状态 ==="
failed=0
for dir in test-repos/* val-repos/* cutoff-repos/*; do
  if [ -d "$dir" ]; then
    count=$(find "$dir" -name "*.vo" 2>/dev/null | wc -l)
    if [ "$count" -gt 0 ]; then
      echo "✅ $(basename $dir): $count .vo 文件"
    else
      echo "❌ $(basename $dir): 未构建"
      failed=$((failed + 1))
    fi
  fi
done

if [ "$failed" -gt 0 ]; then
  echo ""
  echo "构建失败：$failed 个项目没有产出 .vo 文件。"
  exit 1
fi

echo ""
echo "全部项目构建成功。"
