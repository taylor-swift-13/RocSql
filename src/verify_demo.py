#!/usr/bin/env python3
"""
Coq 证明验证工具 - 使用示例

本脚本演示如何使用 verify.py 进行 Coq 证明验证。
"""

from verify import verify_proof, get_theorem_info, list_theorems


def demo_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("基本使用示例")
    print("=" * 60)
    
    # 示例 1: 验证正确证明
    print("\n1. 验证正确证明:")
    proof = """Proof.
intros a b1 b2 l H; inversion H; auto.
Qed."""
    
    result = verify_proof("test:39", proof)
    print(f"   定理 ID: test:39")
    print(f"   状态: {result['state']}")  # proven
    print(f"   描述: {result['proof_status']}")  # 编译成功
    
    # 示例 2: 验证错误证明
    print("\n2. 验证错误证明:")
    bad_proof = "Proof. auto. Qed."
    result = verify_proof("test:39", bad_proof)
    print(f"   状态: {result['state']}")  # failed
    print(f"   描述: {result['proof_status']}")  # 编译失败（证明有误）
    
    # 示例 3: 验证未完成证明
    print("\n3. 验证未完成证明:")
    incomplete_proof = "Proof. intros."
    result = verify_proof("test:39", incomplete_proof)
    print(f"   状态: {result['state']}")  # in_progress
    print(f"   描述: {result['proof_status']}")  # 编译失败（证明未完成）


def demo_get_theorem_info():
    """获取定理信息示例"""
    print("\n" + "=" * 60)
    print("获取定理信息")
    print("=" * 60)
    
    info = get_theorem_info("test:39")
    print(f"\n定理 ID: {info['theorem_id']}")
    print(f"项目名称: {info['project']}")
    print(f"文件路径: {info['file']}")
    print(f"定理行号: {info['theorem_line']}")
    print(f"证明开始行: {info['proof_start_line']}")
    print(f"证明结束行: {info['proof_end_line']}")
    print(f"\n定理陈述:\n{info['statement'][:200]}...")


def demo_list_theorems():
    """列注定理示例"""
    print("\n" + "=" * 60)
    print("列注定理")
    print("=" * 60)
    
    # 列出 test split 的前 5 个定理
    theorems = list_theorems("test", limit=5)
    print(f"\n找到 {len(theorems)} 个定理:\n")
    
    for thm in theorems:
        print(f"  {thm['theorem_id']}")
        print(f"    项目: {thm['project']}")
        print(f"    文件: {thm['file']}")
        print(f"    陈述: {thm['statement'][:100]}...")
        print()


def demo_interpret_results():
    """结果解读指南"""
    print("\n" + "=" * 60)
    print("验证结果解读")
    print("=" * 60)
    
    print("""
验证结果 (result['state']):
  
  ✅ "proven" - 证明验证成功
     - 证明语法正确
     - 逻辑推理正确
     - 成功到达 Qed.
  
  ❌ "failed" - 证明有错误
     - 包含 Qed. 但证明过程有误
     - 可能是语法错误或逻辑错误
  
  ⏸️  "in_progress" - 证明未完成
     - 缺少 Qed. 
     - 需要更多证明步骤
  
  ⚠️ "error" - 系统错误或依赖缺失
     - 原文件编译失败（缺少依赖）
     - 文件读取错误
     - 编译超时

其他重要字段:
  - result['error_message']: 错误详细信息
  - result['proof_status']: 状态描述
  - result['verification_method']: "coqc" 表示真正编译验证
  - result['temp_file']: 临时文件路径（用于调试）
""")


if __name__ == "__main__":
    demo_basic_usage()
    demo_get_theorem_info()
    demo_list_theorems()
    demo_interpret_results()
    
    print("\n" + "=" * 60)
    print("示例完成！")
    print("=" * 60)
