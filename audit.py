#!/usr/bin/env python3
"""Cross-file and scientific-payload audit for the standalone repository.

The audit binds retained input IDs to their full payloads, certificates, checker
returns, result rows, and summary fields.  It does not regenerate search
certificates, but it independently re-executes every retained factor schedule
through the legality checker; ``run.py check`` performs the same full binding.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from run import verify_retained_payloads


class AuditError(ValueError):pass


def load_json(root:Path,relative:str)->Any:
    path=root/relative
    if not path.is_file():raise AuditError(f'missing JSON file: {relative}')
    try:return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:raise AuditError(f'invalid JSON in {relative}: {exc}') from exc


def load_csv(root:Path,relative:str)->list[dict[str,str]]:
    path=root/relative
    if not path.is_file():raise AuditError(f'missing CSV file: {relative}')
    with path.open(newline='',encoding='utf-8') as handle:
        reader=csv.DictReader(handle)
        if not reader.fieldnames:raise AuditError(f'CSV has no header: {relative}')
        rows=list(reader)
    if not rows:raise AuditError(f'CSV has no data rows: {relative}')
    return rows


def unique(rows:list[dict[str,str]],field:str,label:str)->set[str]:
    values=[row.get(field,'').strip() for row in rows]
    if any(not value for value in values):raise AuditError(f'{label}: blank {field}')
    if len(values)!=len(set(values)):raise AuditError(f'{label}: duplicate {field}')
    return set(values)


def verify_evidence_paths(root:Path,claims:list[dict[str,str]])->int:
    pattern=re.compile(r'(?:proofs|src|formal|tests|results|inputs)/[A-Za-z0-9_.\-/]+')
    checked=set()
    for row in claims:
        for field in ('proof_or_checker','source_or_test','raw_result'):
            for match in pattern.findall(row.get(field,'')):
                relative=match.rstrip('.,;:')
                if not (root/relative).exists():raise AuditError(f"claim {row['claim_id']}: missing evidence path {relative}")
                checked.add(relative)
    return len(checked)


def audit(root:Path=ROOT,package_clean:bool=False)->dict[str,Any]:
    root=Path(root).resolve()
    required=['README.md','readme.txt','LICENSE','run.py','audit.py','claim_evidence_ledger.csv',
        'external_resources.csv','reference-audit.csv','literature-notes.md','proofs/capability.md',
        'proofs/replay.md','proofs/residual.md','proofs/integer-rank.md','proofs/cache.md','formal/check.py',
        'results/summary.json','results/pilot.json','results/rectangle_negative.json','inputs/rectangle_negative.json']
    missing=[name for name in required if not (root/name).is_file()]
    if missing:raise AuditError(f'required files missing: {missing}')

    try:payload=verify_retained_payloads(root,execute_schedules=True)
    except (AssertionError,KeyError,TypeError,ValueError) as exc:raise AuditError(f'scientific payload mismatch: {exc}') from exc

    references=load_csv(root,'reference-audit.csv');reference_keys=unique(references,'key','reference audit')
    persistent=unique(references,'persistent_id','reference audit')
    if len(references)!=81:raise AuditError(f'reference audit must contain the cited 81 sources, found {len(references)}')
    for row in references:
        if not row['persistent_id'].startswith(('doi:','arXiv:','https://doi.org/','https://arxiv.org/','https://')):
            raise AuditError(f"reference {row['key']}: unsupported persistent identifier")
        if not row.get('verification_basis','').strip() or not row.get('technical_role','').strip():
            raise AuditError(f"reference {row['key']}: incomplete audit metadata")
        if not row.get('cited_in','').strip():raise AuditError(f"reference {row['key']}: no manuscript citation location")

    claims=load_csv(root,'claim_evidence_ledger.csv');claim_ids=unique(claims,'claim_id','claim evidence ledger')
    for row in claims:
        for field in ('claim','maturity','boundary','fresh_recheck'):
            if not row.get(field,'').strip():raise AuditError(f"claim {row['claim_id']}: blank {field}")
    evidence_paths=verify_evidence_paths(root,claims)

    resources=load_csv(root,'external_resources.csv');resource_ids=unique(resources,'id','external resources')
    for row in resources:
        if not row.get('scholarly_or_official_url','').startswith('https://'):
            raise AuditError(f"external resource {row['id']}: non-HTTPS scholarly URL")
        if row.get('internals_modified') not in {'yes','no'}:
            raise AuditError(f"external resource {row['id']}: invalid internals_modified value")

    archives=sorted(str(path.relative_to(root)) for path in root.rglob('*')
                    if path.is_file() and path.suffix.lower() in {'.zip','.tar','.gz','.7z'})
    if archives:raise AuditError(f'nested archives are not allowed: {archives}')
    cache_dirs=sorted(str(path.relative_to(root)) for path in root.rglob('__pycache__') if path.is_dir())
    bytecode=sorted(str(path.relative_to(root)) for path in root.rglob('*.pyc'))
    if package_clean and (cache_dirs or bytecode):
        raise AuditError(f'generated Python cache files present: dirs={cache_dirs}, files={bytecode[:5]}')

    return {'status':'pass',**payload,'reference_records':len(reference_keys),
        'persistent_reference_ids':len(persistent),'claim_records':len(claim_ids),
        'evidence_paths_checked':evidence_paths,'external_resource_records':len(resource_ids),
        'package_clean_mode':package_clean,'python_cache_directories':len(cache_dirs),
        'python_bytecode_files':len(bytecode)}


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package-clean',action='store_true',help='also reject generated __pycache__ directories and .pyc files')
    args=parser.parse_args()
    try:report=audit(ROOT,package_clean=args.package_clean)
    except (AuditError,KeyError,TypeError,ValueError) as exc:
        print(f'AUDIT FAILED: {exc}');raise SystemExit(1)
    print(json.dumps(report,indent=2,sort_keys=True))


if __name__=='__main__':main()
