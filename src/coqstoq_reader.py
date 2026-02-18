#!/usr/bin/env python3
"""
CoqStoq Proof Problem Reader

This program reads proof problems from the CoqStoq benchmark dataset.
It can extract theorem statements and proof contexts from the various splits
(test, validation, cutoff) without requiring the full CoqStoq environment.
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class Split(Enum):
    """Available data splits in CoqStoq"""
    TEST = "test"
    VAL = "val" 
    CUTOFF = "cutoff"


@dataclass
class Position:
    """Position in a source file"""
    line: int
    column: int
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        return cls(line=data['line'], column=data['column'])


@dataclass
class Project:
    """Project information"""
    dir_name: str
    split_dir_name: str
    thm_dir_name: str
    commit_hash: str
    compile_args: List[str]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        split_info = data['split']
        return cls(
            dir_name=data['dir_name'],
            split_dir_name=split_info['dir_name'],
            thm_dir_name=split_info['thm_dir_name'],
            commit_hash=data['commit_hash'],
            compile_args=data['compile_args']
        )


@dataclass
class EvalTheorem:
    """A theorem evaluation problem from CoqStoq"""
    project: Project
    path: str  # relative path in the project
    theorem_start_pos: Position  # inclusive
    theorem_end_pos: Position  # inclusive line, exclusive column
    proof_start_pos: Position  # inclusive
    proof_end_pos: Position  # inclusive line, exclusive column
    hash: str  # Hash of file when theorem was collected
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvalTheorem':
        return cls(
            project=Project.from_dict(data['project']),
            path=data['path'],
            theorem_start_pos=Position.from_dict(data['theorem_start_pos']),
            theorem_end_pos=Position.from_dict(data['theorem_end_pos']),
            proof_start_pos=Position.from_dict(data['proof_start_pos']),
            proof_end_pos=Position.from_dict(data['proof_end_pos']),
            hash=data['hash']
        )


class CoqStoqReader:
    """Reader for CoqStoq benchmark data"""
    
    def __init__(self, coqstoq_path: str):
        """
        Initialize the reader with path to CoqStoq directory
        
        Args:
            coqstoq_path: Path to the CoqStoq directory
        """
        self.coqstoq_path = Path(coqstoq_path)
        if not self.coqstoq_path.exists():
            raise FileNotFoundError(f"CoqStoq directory not found: {coqstoq_path}")
    
    def get_theorem_list_file(self, split: Split) -> Path:
        """Get the path to the theorem list file for a split"""
        filename = f"{split.value}-theorems.json"
        return self.coqstoq_path / filename
    
    def get_theorem_count(self, split: Split) -> int:
        """Get the number of theorems in a split"""
        theorem_list_file = self.get_theorem_list_file(split)
        if not theorem_list_file.exists():
            return 0
        
        with open(theorem_list_file, 'r') as f:
            theorem_list = json.load(f)
        return len(theorem_list)
    
    def load_theorem_from_file(self, thm_path: str, thm_idx: int) -> EvalTheorem:
        """Load a specific theorem from a theorem file"""
        full_path = self.coqstoq_path / thm_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"Theorem file not found: {full_path}")
        
        with open(full_path, 'r') as f:
            theorems = json.load(f)
        
        if thm_idx >= len(theorems):
            raise IndexError(f"Theorem index {thm_idx} out of range for file {thm_path}")
        
        return EvalTheorem.from_dict(theorems[thm_idx])
    
    def get_theorem(self, split: Split, index: int) -> EvalTheorem:
        """Get a theorem by index from a split"""
        theorem_list_file = self.get_theorem_list_file(split)
        
        with open(theorem_list_file, 'r') as f:
            theorem_list = json.load(f)
        
        if index >= len(theorem_list):
            raise IndexError(f"Index {index} out of range for {split.value} split")
        
        thm_info = theorem_list[index]
        return self.load_theorem_from_file(thm_info['thm_path'], thm_info['thm_idx'])
    
    def get_theorems(self, split: Split, start: int = 0, count: Optional[int] = None) -> List[EvalTheorem]:
        """Get multiple theorems from a split"""
        theorem_list_file = self.get_theorem_list_file(split)
        
        with open(theorem_list_file, 'r') as f:
            theorem_list = json.load(f)
        
        end = len(theorem_list) if count is None else min(start + count, len(theorem_list))
        theorems = []
        
        for i in range(start, end):
            thm_info = theorem_list[i]
            try:
                theorem = self.load_theorem_from_file(thm_info['thm_path'], thm_info['thm_idx'])
                theorems.append(theorem)
            except (FileNotFoundError, IndexError) as e:
                print(f"Warning: Could not load theorem {i}: {e}")
                continue
        
        return theorems
    
    def get_source_file_content(self, theorem: EvalTheorem) -> str:
        """Get the content of the source file containing the theorem"""
        project_path = self.coqstoq_path / theorem.project.split_dir_name / theorem.project.dir_name
        source_file = project_path / theorem.path
        
        if not source_file.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")
        
        with open(source_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def extract_theorem_statement(self, theorem: EvalTheorem) -> str:
        """Extract the theorem statement from the source file"""
        content = self.get_source_file_content(theorem)
        lines = content.split('\n')
        
        start_line = theorem.theorem_start_pos.line - 1  # Convert to 0-based
        end_line = theorem.theorem_end_pos.line - 1
        
        if start_line == end_line:
            # Single line theorem
            line = lines[start_line]
            return line[theorem.theorem_start_pos.column:theorem.theorem_end_pos.column]
        else:
            # Multi-line theorem
            result_lines = []
            # First line
            result_lines.append(lines[start_line][theorem.theorem_start_pos.column:])
            # Middle lines
            for i in range(start_line + 1, end_line):
                result_lines.append(lines[i])
            # Last line
            result_lines.append(lines[end_line][:theorem.theorem_end_pos.column])
            
            return '\n'.join(result_lines)
    
    def extract_proof(self, theorem: EvalTheorem) -> str:
        """Extract the proof from the source file"""
        content = self.get_source_file_content(theorem)
        lines = content.split('\n')
        
        start_line = theorem.proof_start_pos.line - 1  # Convert to 0-based
        end_line = theorem.proof_end_pos.line - 1
        
        if start_line == end_line:
            # Single line proof
            line = lines[start_line]
            return line[theorem.proof_start_pos.column:theorem.proof_end_pos.column]
        else:
            # Multi-line proof
            result_lines = []
            # First line
            result_lines.append(lines[start_line][theorem.proof_start_pos.column:])
            # Middle lines
            for i in range(start_line + 1, end_line):
                result_lines.append(lines[i])
            # Last line
            result_lines.append(lines[end_line][:theorem.proof_end_pos.column])
            
            return '\n'.join(result_lines)
    
    def print_theorem_info(self, theorem: EvalTheorem):
        """Print detailed information about a theorem"""
        print(f"Project: {theorem.project.dir_name}")
        print(f"File: {theorem.path}")
        print(f"Hash: {theorem.hash}")
        print(f"Theorem position: Line {theorem.theorem_start_pos.line}-{theorem.theorem_end_pos.line}")
        print(f"Proof position: Line {theorem.proof_start_pos.line}-{theorem.proof_end_pos.line}")
        
        try:
            theorem_stmt = self.extract_theorem_statement(theorem)
            print(f"\nTheorem statement:\n{theorem_stmt}")
            
            proof = self.extract_proof(theorem)
            print(f"\nProof:\n{proof}")
        except FileNotFoundError as e:
            print(f"Could not extract content: {e}")


def main():
    """Example usage of the CoqStoq reader"""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python coqstoq_reader.py <path_to_coqstoq>")
        sys.exit(1)
    
    coqstoq_path = sys.argv[1]
    
    try:
        reader = CoqStoqReader(coqstoq_path)
        
        # Print statistics
        print("CoqStoq Dataset Statistics:")
        for split in Split:
            count = reader.get_theorem_count(split)
            print(f"  {split.value.capitalize()} split: {count} theorems")
        
        print("\n" + "="*50)
        
        # Show a few examples from test split
        print("Example theorems from test split:")
        test_theorems = reader.get_theorems(Split.TEST, start=0, count=3)
        
        for i, theorem in enumerate(test_theorems):
            print(f"\n--- Example {i+1} ---")
            reader.print_theorem_info(theorem)
            print()
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()