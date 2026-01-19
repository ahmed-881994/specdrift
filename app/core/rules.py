"""
Diff rules for classifying API changes.

This module defines the exact rules for classifying changes as breaking,
potentially breaking, or non-breaking.
"""

# BREAKING CHANGES
BREAKING_RULES = {
    "endpoint_removed": "Endpoint removed",
    "method_removed": "HTTP method removed",
    "required_parameter_added": "Required request parameter added",
    "parameter_removed": "Parameter removed",
    "parameter_type_changed": "Parameter type changed",
    "required_field_added": "Required request body field added",
    "field_removed": "Request/response field removed",
    "field_type_changed": "Field type changed",
    "enum_value_removed": "Enum value removed",
    "success_response_removed": "Success response (2xx) removed",
}

# POTENTIALLY BREAKING CHANGES
POTENTIALLY_BREAKING_RULES = {
    "non_2xx_response_removed": "Non-2xx response removed",
    "enum_value_added": "Enum value added",
    "default_value_removed": "Default value removed",
}

# NON-BREAKING CHANGES
NON_BREAKING_RULES = {
    "endpoint_added": "New endpoint",
    "method_added": "New HTTP method",
    "optional_parameter_added": "New optional parameter",
    "optional_field_added": "New optional request field",
    "response_field_added": "New response field",
    "metadata_changed": "Metadata-only changes",
}


def classify_change(rule_type: str) -> str:
    """
    Classify a change based on its rule type.
    
    Args:
        rule_type: The type of change/rule
        
    Returns:
        Classification: "breaking", "potentially_breaking", or "non_breaking"
    """
    if rule_type in BREAKING_RULES:
        return "breaking"
    elif rule_type in POTENTIALLY_BREAKING_RULES:
        return "potentially_breaking"
    elif rule_type in NON_BREAKING_RULES:
        return "non_breaking"
    else:
        # Default to potentially_breaking if uncertain
        return "potentially_breaking"


def get_rule_message(rule_type: str) -> str:
    """
    Get human-readable message for a rule.
    
    Args:
        rule_type: The type of rule
        
    Returns:
        Human-readable message
    """
    return (
        BREAKING_RULES.get(rule_type) or
        POTENTIALLY_BREAKING_RULES.get(rule_type) or
        NON_BREAKING_RULES.get(rule_type) or
        "Unknown change"
    )
