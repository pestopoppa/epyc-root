#!/usr/bin/env python3
"""Validate explicit-key local registrations; emit a review fragment, never priors."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
from pathlib import Path

import yaml


class UniqueLoader(yaml.SafeLoader):
    """Do not silently overwrite a benchmark repeated in a YAML mapping."""


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in result:
            raise ValueError(f'duplicate YAML key: {key}')
        result[key] = loader.construct_object(value_node, deep=True)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def validate_catalog(catalog):
    if type(catalog.get('schema_version')) is not int or catalog['schema_version'] != 1:
        raise ValueError('public_benchmarks schema_version must be 1')
    axes = catalog['axes']
    if not isinstance(axes, dict) or not axes:
        raise ValueError('explicit benchmark-to-axis mapping required')
    for key, axis in axes.items():
        if not isinstance(key, str) or not re.fullmatch(r'[a-z][a-z0-9_]*', key):
            raise ValueError('invalid benchmark key')
        if not isinstance(axis, str) or not axis:
            raise ValueError('axis must be a nonempty string')
    if set(axes) & set(axes.values()):
        raise ValueError('axis names cannot be benchmark keys')
    if not set(catalog.get('universal_keys', [])) <= set(axes):
        raise ValueError('unknown universal benchmark key')
    for model, record in catalog['models'].items():
        vendor = record.get('benchmarks', {})
        local = record.get('local_benchmarks', {})
        absent = record.get('absent_from_card', [])
        if not isinstance(vendor, dict) or not isinstance(local, dict) or not isinstance(absent, list):
            raise ValueError(f'{model}: invalid benchmark fields')
        if len(absent) != len(set(absent)):
            raise ValueError(f'{model}: duplicate absent key')
        if not (set(vendor) | set(local) | set(absent)) <= set(axes):
            raise ValueError(f'{model}: unknown benchmark key')
        if set(vendor) & set(absent):
            raise ValueError(f'{model}: vendor score contradicts absent_from_card')
        for key, value in list(vendor.items()) + list(local.items()):
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError(f'{model}/{key}: invalid score')


def registration_fragment(catalog, registrations):
    """Stage schema-compatible local values without conflating instruments or adopting them.

    New instruments must first receive their own key in the supplied catalog.
    Source pins are caller attestations, carried for review rather than verified here.
    """
    validate_catalog(catalog)
    staged = copy.deepcopy(catalog)
    touched = {}
    seen = set()
    if not registrations:
        raise ValueError('at least one result required')
    for result in registrations:
        model, key = result['model'], result['benchmark_key']
        if model not in staged['models'] or key not in staged['axes']:
            raise ValueError('unknown model or benchmark key; register exact instrument first')
        if (model, key) in seen:
            raise ValueError('duplicate model/benchmark result')
        seen.add((model, key))
        value = result['value']
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError('local correctness score must be finite and normalized')
        source = result['source']
        if not source.get('path') or not (
            re.fullmatch(r'[0-9a-f]{64}', source.get('sha256', '')) or
            (source.get('repo') and re.fullmatch(r'[0-9a-f]{40}', source.get('git_object', '')))
        ):
            raise ValueError('source path and SHA-256 or repo/git object required')
        record = staged['models'][model]
        missing = key not in record.get('benchmarks', {})
        if type(result['absent_from_card']) is not bool or result['absent_from_card'] != missing:
            raise ValueError('explicit vendor absence disclosure disagrees with catalog')
        local = record.setdefault('local_benchmarks', {})
        if key in local and local[key] != value:
            raise ValueError('refusing to overwrite an existing local result')
        local[key] = value
        absent = record.setdefault('absent_from_card', [])
        if missing and key not in absent:
            absent.append(key)
        fragment = touched.setdefault(model, {'local_benchmarks': {}, 'absent_from_card': absent})
        fragment['local_benchmarks'][key] = value
    validate_catalog(staged)
    return {'schema': 'epyc.cj_public_registration.v1',
            'public_benchmarks_fragment': {'schema_version': 1, 'models': touched},
            'sources': copy.deepcopy(registrations), 'routing_prior_or_adoption': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--results', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    if bool(args.results) != bool(args.out):
        parser.error('--results and --out must be supplied together')
    if args.out and args.out.resolve() in {args.catalog.resolve(), args.results.resolve()}:
        parser.error('output must not overwrite catalog or input results')
    raw = args.catalog.read_bytes()
    catalog = yaml.load(raw, Loader=UniqueLoader)
    validate_catalog(catalog)
    if args.results:
        results_raw = args.results.read_bytes()
        packet = registration_fragment(catalog, yaml.load(results_raw, Loader=UniqueLoader))
        packet['catalog_sha256'] = hashlib.sha256(raw).hexdigest()
        packet['results_sha256'] = hashlib.sha256(results_raw).hexdigest()
        args.out.write_text(json.dumps(packet, sort_keys=True, indent=2) + '\n')
    else:
        print(f'PASS: {len(catalog["models"])} models; {len(catalog["axes"])} exact benchmark keys')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
