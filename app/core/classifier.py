"""
Change classifier.

Classifies detected changes into breaking, potentially breaking, and non-breaking categories.
"""

from typing import Dict, Any, Optional
from app.core.rules import classify_change, get_rule_message
from app.models.change import Change


class Classifier:
    """Classifies API changes based on rules."""

    @staticmethod
    def classify_endpoint_removal(path: str) -> Change:
        """Classify endpoint removal as breaking."""
        return Change(
            type="breaking",
            category="endpoint",
            path=path,
            message=get_rule_message("endpoint_removed"),
        )

    @staticmethod
    def classify_endpoint_addition(path: str) -> Change:
        """Classify endpoint addition as non-breaking."""
        return Change(
            type="non_breaking",
            category="endpoint",
            path=path,
            message=get_rule_message("endpoint_added"),
        )

    @staticmethod
    def classify_method_removal(path: str, method: str) -> Change:
        """Classify method removal as breaking."""
        return Change(
            type="breaking",
            category="method",
            path=path,
            method=method.upper(),
            message=get_rule_message("method_removed"),
        )

    @staticmethod
    def classify_method_addition(path: str, method: str) -> Change:
        """Classify method addition as non-breaking."""
        return Change(
            type="non_breaking",
            category="method",
            path=path,
            method=method.upper(),
            message=get_rule_message("method_added"),
        )

    @staticmethod
    def classify_parameter_change(
        path: str,
        method: str,
        param_name: str,
        change_type: str,
        is_required: bool = False,
    ) -> Change:
        """
        Classify parameter changes.
        
        Args:
            path: The API path
            method: The HTTP method
            param_name: The parameter name
            change_type: Type of change (added, removed, type_changed)
            is_required: Whether the parameter is required
            
        Returns:
            Classified change
        """
        if change_type == "removed":
            return Change(
                type="breaking",
                category="parameter",
                path=path,
                method=method.upper(),
                field=param_name,
                message=get_rule_message("parameter_removed"),
            )
        elif change_type == "added":
            if is_required:
                return Change(
                    type="breaking",
                    category="parameter",
                    path=path,
                    method=method.upper(),
                    field=param_name,
                    message=get_rule_message("required_parameter_added"),
                )
            else:
                return Change(
                    type="non_breaking",
                    category="parameter",
                    path=path,
                    method=method.upper(),
                    field=param_name,
                    message=get_rule_message("optional_parameter_added"),
                )
        elif change_type == "type_changed":
            return Change(
                type="breaking",
                category="parameter",
                path=path,
                method=method.upper(),
                field=param_name,
                message=get_rule_message("parameter_type_changed"),
            )
        else:
            return Change(
                type="potentially_breaking",
                category="parameter",
                path=path,
                method=method.upper(),
                field=param_name,
                message="Parameter changed",
            )

    @staticmethod
    def classify_schema_change(
        path: str,
        method: str,
        field_name: str,
        change_type: str,
        is_required: bool = False,
    ) -> Change:
        """
        Classify schema/field changes.
        
        Args:
            path: The API path
            method: The HTTP method
            field_name: The field name
            change_type: Type of change (added, removed, type_changed)
            is_required: Whether the field is required
            
        Returns:
            Classified change
        """
        if change_type == "removed":
            return Change(
                type="breaking",
                category="schema",
                path=path,
                method=method.upper(),
                field=field_name,
                message=get_rule_message("field_removed"),
            )
        elif change_type == "added":
            if is_required:
                return Change(
                    type="breaking",
                    category="schema",
                    path=path,
                    method=method.upper(),
                    field=field_name,
                    message=get_rule_message("required_field_added"),
                )
            else:
                return Change(
                    type="non_breaking",
                    category="schema",
                    path=path,
                    method=method.upper(),
                    field=field_name,
                    message=get_rule_message("optional_field_added"),
                )
        elif change_type == "type_changed":
            return Change(
                type="breaking",
                category="schema",
                path=path,
                method=method.upper(),
                field=field_name,
                message=get_rule_message("field_type_changed"),
            )
        else:
            return Change(
                type="potentially_breaking",
                category="schema",
                path=path,
                method=method.upper(),
                field=field_name,
                message="Field changed",
            )

    @staticmethod
    def classify_response_change(
        path: str, method: str, status_code: str, change_type: str
    ) -> Change:
        """
        Classify response changes.
        
        Args:
            path: The API path
            method: The HTTP method
            status_code: The HTTP status code
            change_type: Type of change (added, removed)
            
        Returns:
            Classified change
        """
        if change_type == "removed":
            if status_code.startswith("2"):
                return Change(
                    type="breaking",
                    category="response",
                    path=path,
                    method=method.upper(),
                    field=f"Response {status_code}",
                    message=get_rule_message("success_response_removed"),
                )
            else:
                return Change(
                    type="potentially_breaking",
                    category="response",
                    path=path,
                    method=method.upper(),
                    field=f"Response {status_code}",
                    message=get_rule_message("non_2xx_response_removed"),
                )
        elif change_type == "added":
            return Change(
                type="non_breaking",
                category="response",
                path=path,
                method=method.upper(),
                field=f"Response {status_code}",
                message="New response status",
            )
        else:
            return Change(
                type="potentially_breaking",
                category="response",
                path=path,
                method=method.upper(),
                field=f"Response {status_code}",
                message="Response changed",
            )
