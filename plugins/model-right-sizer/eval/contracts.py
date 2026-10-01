# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Shared blueprint validation, usable from a standalone installed skill."""
from jsonschema import Draft202012Validator

NON_REFERENCE_HANDOFFS = {"none", "route_via_query_layer"}


def validate(schema: dict, instance: dict) -> list[str]:
    errors = sorted(Draft202012Validator(schema).iter_errors(instance),
                    key=lambda e: [str(p) for p in e.path])
    if errors:
        return [f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors]
    valid_refs = {row['id'] for row in instance['message_schemas']} | NON_REFERENCE_HANDOFFS
    result = []
    for group in ('blueprint_rows', 'work_routing_map'):
        for row in instance[group]:
            if row['handoff_schema_ref'] not in valid_refs:
                result.append(f"{group}[id={row['id']!r}].handoff_schema_ref: "
                              f"{row['handoff_schema_ref']!r} does not match any message_schemas[].id "
                              f"(and isn't {sorted(NON_REFERENCE_HANDOFFS)!r})")
    return result
