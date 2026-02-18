#!/bin/bash
# 批量构建所有 CoqStoq 项目

export PATH="/root/.opam/coqswitch/bin:$PATH"

cd /root/paddlejob/workspace/env_run/output/qwen3/coq/CoqStoq

echo "=============================================="
echo "批量构建所有 CoqStoq 项目"
echo "=============================================="
echo ""

# 构建函数
build_project() {
    local project_dir=$1
    local project_name=$(basename "$project_dir")
    
    echo "构建 $project_name..."
    
    cd "$project_dir"
    
    # 清理旧的构建
    make clean 2>/dev/null || true
    rm -f *.vo *.glob 2>/dev/null
    rm -f theories/*.vo theories/*.glob 2>/dev/null
    
    # 生成 Makefile
    if [ -f "_CoqProject" ]; then
        coq_makefile -f _CoqProject -o Makefile.coq 2>/dev/null
        if [ -f "Makefile.coq" ]; then
            make -f Makefile.coq -j4 2>&1 | tail -5
        fi
    elif [ -f "Makefile" ]; then
        make -j4 2>&1 | tail -5
    else
        echo "  无构建文件"
    fi
    
    cd - > /dev/null
}

# Test repos
echo "=== Test Repositories ==="
for dir in test-repos/*; do
    if [ -d "$dir" ]; then
        build_project "$dir"
    fi
done

# Val repos
echo ""
echo "=== Val Repositories ==="
for dir in val-repos/*; do
    if [ -d "$dir" ]; then
        build_project "$dir"
    fi
done

# Cutoff repos
echo ""
echo "=== Cutoff Repositories ==="
for dir in cutoff-repos/*; do
    if [ -d "$dir" ]; then
        build_project "$dir"
    fi
done

echo ""
echo "=============================================="
echo "构建完成"
echo "=============================================="
