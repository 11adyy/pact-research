#!/usr/bin/env python3
"""
Script to automatically fix binding-capability input mismatches.

This script scans all bindings and corrects their request templates
to reference the correct input names from their corresponding capabilities.
"""

import sys
from pathlib import Path
from typing import Dict, Set

                     
runtime_root = Path(__file__).parent / "runtime"
sys.path.insert(0, str(runtime_root))

import yaml
from runtime.binding_registry import BindingRegistry
from runtime.capability_loader import YamlCapabilityLoader


def fix_binding_inputs():
    """Automatically fix binding-capability input mismatches."""

                           
    registry_root = Path(__file__).parent.parent / "pact-registry"
    runtime_root = Path(__file__).parent

    capability_loader = YamlCapabilityLoader(registry_root)
    binding_registry = BindingRegistry(runtime_root, registry_root)

                      
    all_bindings = binding_registry.list_bindings()

    print(f"Analyzing {len(all_bindings)} bindings for fixes...")

    fixes_applied = []

    for binding in all_bindings:
        try:
                                
            capability = capability_loader.get_capability(binding.capability_id)

                                           
            request_template = binding.request_template
            capability_inputs = set(capability.inputs.keys())

                                                    
            referenced_inputs = set()
            _collect_template_inputs(request_template, referenced_inputs)

                                      
            missing_inputs = referenced_inputs - capability_inputs
            if missing_inputs:
                                          
                fixed_template = _fix_template_inputs(
                    request_template, capability_inputs, missing_inputs
                )
                if fixed_template != request_template:
                                   
                    _apply_binding_fix(binding, fixed_template, runtime_root)
                    fixes_applied.append(
                        {
                            "binding_id": binding.id,
                            "capability_id": binding.capability_id,
                            "original_missing": sorted(missing_inputs),
                            "fixed": True,
                        }
                    )
                else:
                    fixes_applied.append(
                        {
                            "binding_id": binding.id,
                            "capability_id": binding.capability_id,
                            "original_missing": sorted(missing_inputs),
                            "fixed": False,
                            "reason": "Could not determine correct mapping",
                        }
                    )

        except Exception as e:
            fixes_applied.append(
                {"binding_id": binding.id, "error": str(e), "fixed": False}
            )

    return fixes_applied


def _collect_template_inputs(template: dict, inputs: Set[str]):
    """Recursively collect all input.* references from a template."""
    for key, value in template.items():
        if isinstance(value, str) and value.startswith("input."):
            input_name = value[len("input.") :]
            inputs.add(input_name)
        elif isinstance(value, dict):
            _collect_template_inputs(value, inputs)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _collect_template_inputs(item, inputs)


def _fix_template_inputs(
    template: dict, available_inputs: Set[str], missing_inputs: Set[str]
) -> dict:
    """Attempt to fix input references in a template."""
                                                            
    input_mapping = _guess_input_mapping(missing_inputs, available_inputs)

    if not input_mapping:
        return template                     

                                       
    return _apply_input_mapping(template, input_mapping)


def _guess_input_mapping(
    missing_inputs: Set[str], available_inputs: Set[str]
) -> Dict[str, str]:
    """Guess the correct mapping from missing inputs to available ones."""
    mapping = {}

                                                          
    patterns = [
                               
        (["goal"], ["objective"]),
        (["audio_data"], ["audio"]),
        (["json_string"], ["text"]),
        (["email_id"], ["mailbox"]),
        (["image_data"], ["image"]),
        (["pdf_data"], ["path"]),
        (["url"], ["content"]),
        (["categories"], ["labels"]),
                                                 
        (["agents", "query"], ["input"]),                     
        (["frame_rate", "video_data"], ["video"]),                       
        (["code_after", "code_before"], ["code_a", "code_b"]),
        (["filter_criteria", "table_data"], ["condition", "table"]),
        (["channel"], ["message", "recipient"]),
                                            
        (["image_data"], ["image", "labels"]),                         
        (["categories"], ["labels", "text"]),                        
    ]

    for missing, available in patterns:
        missing_set = set(missing)
        set(available)

        if missing_set == missing_inputs:
                                                    
                                                                                                   
            if len(missing) > len(available):
                for m in missing:
                    mapping[m] = available[0]
            else:
                for m, a in zip(missing, available):
                    mapping[m] = a
            break

    return mapping


def _apply_input_mapping(template: dict, mapping: Dict[str, str]) -> dict:
    """Apply input name mapping to a template."""
    result = {}

    for key, value in template.items():
        if isinstance(value, str) and value.startswith("input."):
            input_name = value[len("input.") :]
            if input_name in mapping:
                result[key] = f"input.{mapping[input_name]}"
            else:
                result[key] = value
        elif isinstance(value, dict):
            result[key] = _apply_input_mapping(value, mapping)
        elif isinstance(value, list):
            result[key] = [
                _apply_input_mapping(item, mapping) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value

    return result


def _apply_binding_fix(binding, fixed_template: dict, registry_root: Path):
    """Apply the fix to the binding file."""
                                
    binding_path = _find_binding_file(binding.id, registry_root)
    if not binding_path:
        print(f"Warning: Could not find file for binding {binding.id}")
        return

                                   
    with binding_path.open("r", encoding="utf-8") as f:
        binding_data = yaml.safe_load(f)

                                 
    binding_data["request"] = fixed_template

                                  
    with binding_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(binding_data, f, default_flow_style=False, sort_keys=False)

    print(f"Fixed binding: {binding.id}")


def _find_binding_file(binding_id: str, runtime_root: Path) -> Path | None:
    """Find the file path for a binding."""
                                                                   
                                                                  
    if not binding_id.startswith("python_"):
        return None

    capability_part = binding_id[len("python_") :]
                                                                    
    capability_id = capability_part.replace("_", ".")

    binding_file = (
        runtime_root / "bindings" / "official" / capability_id / f"{binding_id}.yaml"
    )
    if binding_file.exists():
        return binding_file

    return None


def main():
    fixes = fix_binding_inputs()

    successful_fixes = [f for f in fixes if f.get("fixed", False)]
    failed_fixes = [f for f in fixes if not f.get("fixed", False)]

    print(f"\n[OK] Successfully fixed {len(successful_fixes)} bindings")
    print(f"[FAIL] Could not fix {len(failed_fixes)} bindings")

    if successful_fixes:
        print("\nFixed bindings:")
        for fix in successful_fixes:
            print(f"  - {fix['binding_id']}: {', '.join(fix['original_missing'])}")

    if failed_fixes:
        print("\nFailed to fix:")
        for fix in failed_fixes:
            if "error" in fix:
                print(f"  - {fix['binding_id']}: Error - {fix['error']}")
            else:
                print(
                    f"  - {fix['binding_id']}: {', '.join(fix['original_missing'])} - {fix.get('reason', 'Unknown')}"
                )

    return 0 if not failed_fixes else 1


if __name__ == "__main__":
    sys.exit(main())
