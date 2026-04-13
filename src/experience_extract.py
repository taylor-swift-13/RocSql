#!/usr/bin/env python3
"""Build retrieval records from CoqStoq gold-reference theorem blocks."""

from __future__ import annotations

import re
from typing import Any, Dict, List

try:
    from retrieval_llm import generate_retrieval_llm_artifacts
    from theorem_task import TheoremTask
except ModuleNotFoundError:
    from .retrieval_llm import generate_retrieval_llm_artifacts
    from .theorem_task import TheoremTask


def _slug(text: str) -> str:
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', text).strip('_') or 'experience'


def _declaration_kind(declaration: str) -> str:
    match = re.match(r"^\s*(Lemma|Theorem|Corollary|Proposition|Fact|Remark)\b", declaration)
    return match.group(1) if match else 'Theorem'


def _coqstoq_item_kind(declaration: str) -> str:
    kind = _declaration_kind(declaration).lower()
    if kind in {'lemma', 'theorem', 'corollary', 'proposition', 'fact', 'remark'}:
        return kind
    return 'theorem'


def infer_proof_shape_tags(text: str) -> List[str]:
    lowered = text.lower()
    tags: List[str] = []
    if 'induction' in lowered or 'elim' in lowered:
        tags.append('induction')
    if 'rewrite' in lowered:
        tags.append('rewrite')
    if 'transitivity' in lowered:
        tags.append('transitivity')
    if 'contradiction' in lowered or 'exfalso' in lowered:
        tags.append('contradiction')
    if 'assert ' in lowered or '\nhave ' in lowered or '\nlemma ' in lowered:
        tags.append('local_lemma')
    if 'auto' in lowered or 'eauto' in lowered:
        tags.append('automation')
    if 'destruct' in lowered or 'case' in lowered:
        tags.append('case_analysis')
    if 'apply ' in lowered:
        tags.append('apply_chain')
    return sorted(set(tags))


def _normalized_theorem_types(task: TheoremTask, proof_texts: List[str]) -> List[str]:
    declaration = task.theorem_declaration
    lowered_decl = declaration.lower()
    combined = ' '.join(proof_texts).lower()
    theorem_types: List[str] = []
    if '<->' in declaration:
        theorem_types.append('iff')
    if '->' in declaration:
        theorem_types.extend(['implication', 'forward_rule'])
    if '==' in declaration or re.search(r'[^<>=]=[^=]', declaration):
        theorem_types.append('equality')
    if any(symbol in declaration for symbol in ('<=', '>=', '<', '>')):
        theorem_types.append('order')
    if any(symbol in declaration for symbol in ('+', '-', '*', '/')) or re.search(r'\b\d+\b', declaration):
        theorem_types.append('arithmetic')
    if 'exists' in lowered_decl:
        theorem_types.append('existential')
    if 'reflect' in lowered_decl:
        theorem_types.extend(['reflection', 'boolean_spec'])
    if 'proper' in lowered_decl or 'setoid' in lowered_decl or 'morphism' in lowered_decl:
        theorem_types.append('setoid')
    if 'rewrite' in combined:
        theorem_types.append('rewrite_rule')
    if 'induction' in combined or 'elim' in combined:
        theorem_types.append('induction')
    if 'destruct' in combined or 'case' in combined:
        theorem_types.append('case_analysis')
    if 'assert ' in combined or '\nhave ' in combined:
        theorem_types.append('local_lemma_pattern')
    if not theorem_types:
        theorem_types.append('structural')
    deduped: List[str] = []
    for item in theorem_types:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _generate_gold_llm_artifacts(task: TheoremTask, proof_block: str) -> Dict[str, str]:
    return generate_retrieval_llm_artifacts(
        locator_label='file_path',
        locator_value=f'{task.project}/{task.file_relpath}',
        kind=_declaration_kind(task.theorem_declaration),
        name=task.theorem_name,
        declaration=task.theorem_declaration,
        proof_text=proof_block,
        supporting_context='',
        model='gpt-5.4-nano',
    )


def _extract_coqstoq_related_items(task: TheoremTask, source_text: str) -> List[Dict[str, str]]:
    decl_re = re.compile(r"^\s*(Lemma|Theorem|Corollary|Proposition|Fact|Remark)\s+([A-Za-z0-9_']+)\b", re.MULTILINE)
    theorem_block = task.extract_theorem_block(source_text)
    proof_text = theorem_block.get('proof_text', '') if theorem_block else ''
    text = ' '.join(part for part in [task.theorem_declaration, proof_text] if part).lower()
    related: List[Dict[str, str]] = []
    for match in decl_re.finditer(source_text):
        kind = match.group(1).lower()
        name = match.group(2)
        if name == task.theorem_name or len(name) < 2:
            continue
        if re.search(rf"\b{re.escape(name.lower())}\b", text):
            related.append({'kind': kind, 'name': name})
    deduped: List[Dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in related:
        key = (entry['kind'], entry['name'])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped[:24]


def build_gold_reference_bundle(task: TheoremTask) -> Dict[str, Any]:
    source_text = task.source_path().read_text(encoding='utf-8')
    theorem_block = task.extract_theorem_block(source_text)
    if theorem_block is None:
        raise ValueError(f'Could not extract theorem block for {task.theorem_id}')
    proof_block = str(theorem_block.get('block', '')).strip()
    proof_text = str(theorem_block.get('proof_text', '')).strip()
    theorem_types = _normalized_theorem_types(task, [proof_text])
    generated = _generate_gold_llm_artifacts(task, proof_block)
    return {
        'record_id': _slug(task.theorem_id),
        'source_theorem_id': task.theorem_id,
        'project': task.project,
        'file_path': task.file_relpath,
        'item_kind': _coqstoq_item_kind(task.theorem_declaration),
        'item_name': task.theorem_name,
        'semantic_explanation': generated['semantic_explanation'],
        'normalized_theorem_types': theorem_types,
        'context': task.theorem_declaration,
        'proof': proof_block,
        'related': _extract_coqstoq_related_items(task, source_text),
        'detail_md': generated['detail_md'],
        'reasoning_md': generated['reasoning_md'],
    }
