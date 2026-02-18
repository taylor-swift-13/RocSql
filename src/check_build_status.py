#!/usr/bin/env python3
"""
CoqStoq 项目构建状态报告生成器
"""

import subprocess
import os
from pathlib import Path

def check_project(project_path):
    """检查项目构建状态"""
    vo_files = list(Path(project_path).rglob("*.vo"))
    return len(vo_files)

def test_theorem(verifier, theorem_id):
    """测试定理验证"""
    try:
        result = verifier.verify_proof(theorem_id, "Proof. auto. Qed.")
        return result['state']
    except Exception as e:
        return f"error: {e}"

def main():
    script_dir = Path(__file__).resolve().parent
    coqstoq_path = script_dir.parent / "CoqStoq"
    
    print("=" * 80)
    print("CoqStoq 项目构建状态报告")
    print("=" * 80)
    print()
    
    # 检查每个 split
    splits = [
        ("test-repos", "Test"),
        ("val-repos", "Val"),
        ("cutoff-repos", "Cutoff")
    ]
    
    total_projects = 0
    built_projects = 0
    
    for split_dir, split_name in splits:
        print(f"\n{split_name} Split:")
        print("-" * 80)
        
        split_path = coqstoq_path / split_dir
        if not split_path.exists():
            print(f"  目录不存在: {split_path}")
            continue
            
        for project_dir in sorted(split_path.iterdir()):
            if project_dir.is_dir():
                total_projects += 1
                project_name = project_dir.name
                vo_count = check_project(project_dir)
                
                if vo_count > 0:
                    built_projects += 1
                    status = f"✅ 已构建 ({vo_count} .vo 文件)"
                else:
                    status = "❌ 未构建"
                
                print(f"  {project_name:<25} {status}")
    
    print()
    print("=" * 80)
    print(f"总计: {built_projects}/{total_projects} 项目已构建")
    print("=" * 80)
    
    # Coq 版本信息
    print("\nCoq 版本信息:")
    try:
        result = subprocess.run(["coqc", "--version"], capture_output=True, text=True)
        print(result.stdout)
    except:
        print("  无法获取 Coq 版本")

if __name__ == "__main__":
    main()
