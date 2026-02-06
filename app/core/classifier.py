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
        param_in: str = "",
        old_type: str = "",
        new_type: str = "",
    ) -> Change:
        """
        Classify parameter changes.
        
        Args:
            path: The API path
            method: The HTTP method
            param_name: The parameter name
            change_type: Type of change (added, removed, type_changed, made_required, made_optional)
            is_required: Whether the parameter is required (for added parameters)
            param_in: Location of parameter (query, path, header, cookie)
            old_type: Old parameter type
            new_type: New parameter type
            
        Returns:
            Classified change
        """
        details = {}
        if param_in:
            details["location"] = param_in
        
        if change_type == "removed":
            return Change(
                type="breaking",
                category="parameter",
                path=path,
                method=method.upper(),
                field_name=param_name,
                message=get_rule_message("parameter_removed"),
                details=details,
            )
        elif change_type == "added":
            details["required"] = is_required
            if is_required:
                return Change(
                    type="breaking",
                    category="parameter",
                    path=path,
                    method=method.upper(),
                    field_name=param_name,
                    message=get_rule_message("required_parameter_added"),
                    details=details,
                )
            else:
                return Change(
                    type="non_breaking",
                    category="parameter",
                    path=path,
                    method=method.upper(),
                    field_name=param_name,
                    message=get_rule_message("optional_parameter_added"),
                    details=details,
                )
        elif change_type == "type_changed":
            if old_type:
                details["old_type"] = old_type
            if new_type:
                details["new_type"] = new_type
            return Change(
                type="breaking",
                category="parameter",
                path=path,
                method=method.upper(),
                field_name=param_name,
                message=get_rule_message("parameter_type_changed"),
                details=details,
            )
        elif change_type == "made_required":
            return Change(
                type="breaking",
                category="parameter",
                path=path,
                method=method.upper(),
                field_name=param_name,
                message=get_rule_message("parameter_made_required"),
                details=details,
            )
        elif change_type == "made_optional":
            return Change(
                type="potentially_breaking",
                category="parameter",
                path=path,
                method=method.upper(),
                field_name=param_name,
                message=get_rule_message("parameter_made_optional"),
                details=details,
            )
        else:
            return Change(
                type="potentially_breaking",
                category="parameter",
                path=path,
                method=method.upper(),
                field_name=param_name,
                message="Parameter changed",
                details=details,
            )

    @staticmethod
    def classify_request_body_change(
        path: str,
        method: str,
        change_type: str,
        is_required: bool = False,
        content_type: str = "",
    ) -> Change:
        """
        Classify request body changes.
        
        Args:
            path: The API path
            method: The HTTP method
            change_type: Type of change (added, removed, made_required, made_optional)
            is_required: Whether the request body is required (for added bodies)
            content_type: Content type of the request body
            
        Returns:
            Classified change
        """
        details = {}
        if content_type:
            details["content_type"] = content_type
        
        if change_type == "removed":
            return Change(
                type="breaking",
                category="request_body",
                path=path,
                method=method.upper(),
                message=get_rule_message("request_body_removed"),
                details=details,
            )
        elif change_type == "added":
            details["required"] = is_required
            if is_required:
                return Change(
                    type="breaking",
                    category="request_body",
                    path=path,
                    method=method.upper(),
                    message=get_rule_message("required_request_body_added"),
                    details=details,
                )
            else:
                return Change(
                    type="non_breaking",
                    category="request_body",
                    path=path,
                    method=method.upper(),
                    message=get_rule_message("optional_request_body_added"),
                    details=details,
                )
        elif change_type == "made_required":
            return Change(
                type="breaking",
                category="request_body",
                path=path,
                method=method.upper(),
                message=get_rule_message("request_body_made_required"),
                details=details,
            )
        elif change_type == "made_optional":
            return Change(
                type="potentially_breaking",
                category="request_body",
                path=path,
                method=method.upper(),
                message=get_rule_message("request_body_made_optional"),
                details=details,
            )
        else:
            return Change(
                type="potentially_breaking",
                category="request_body",
                path=path,
                method=method.upper(),
                message="Request body changed",
                details=details,
            )

    @staticmethod
    def classify_schema_change(
        path: str,
        method: str,
        field_name: str,
        change_type: str,
        location: str = "request_body",
        is_required: bool = False,
        old_type: str = "",
        new_type: str = "",
    ) -> Change:
        """
        Classify schema/field changes.
        
        Args:
            path: The API path
            method: The HTTP method
            field_name: The field name
            change_type: Type of change (added, removed, type_changed, made_required, made_optional)
            location: Location of the change (request_body, response_200, etc.)
            is_required: Whether the field is required (for added fields)
            old_type: Old field type
            new_type: New field type
            
        Returns:
            Classified change
        """
        # Determine if this is a request or response schema
        is_response = location.startswith("response_")
        
        details = {"location": location}
        
        if change_type == "removed":
            return Change(
                type="breaking",
                category="schema",
                path=path,
                method=method.upper(),
                field_name=field_name,
                message=get_rule_message("field_removed"),
                details=details
            )
        elif change_type == "added":
            details["required"] = is_required
            if is_required and not is_response:
                # Required fields in request body are breaking
                return Change(
                    type="breaking",
                    category="schema",
                    path=path,
                    method=method.upper(),
                    field_name=field_name,
                    message=get_rule_message("required_field_added"),
                    details=details
                )
            else:
                # Optional fields or response fields are non-breaking
                return Change(
                    type="non_breaking",
                    category="schema",
                    path=path,
                    method=method.upper(),
                    field_name=field_name,
                    message=get_rule_message("optional_field_added"),
                    details=details
                )
        elif change_type == "type_changed":
            if old_type:
                details["old_type"] = old_type
            if new_type:
                details["new_type"] = new_type
            return Change(
                type="breaking",
                category="schema",
                path=path,
                method=method.upper(),
                field_name=field_name,
                message=get_rule_message("field_type_changed"),
                details=details
            )
        elif change_type == "made_required":
            if not is_response:
                # Making request field required is breaking
                return Change(
                    type="breaking",
                    category="schema",
                    path=path,
                    method=method.upper(),
                    field_name=field_name,
                    message=get_rule_message("field_made_required"),
                    details=details
                )
            else:
                # Making response field required is potentially breaking
                return Change(
                    type="potentially_breaking",
                    category="schema",
                    path=path,
                    method=method.upper(),
                    field_name=field_name,
                    message=get_rule_message("field_made_required"),
                    details=details
                )
        elif change_type == "made_optional":
            return Change(
                type="potentially_breaking",
                category="schema",
                path=path,
                method=method.upper(),
                field_name=field_name,
                message=get_rule_message("field_made_optional"),
                details=details
            )
        else:
            return Change(
                type="potentially_breaking",
                category="schema",
                path=path,
                method=method.upper(),
                field_name=field_name,
                message="Field changed",
                details=details
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
        details = {"status_code": status_code}
        
        if change_type == "removed":
            if status_code.startswith("2"):
                return Change(
                    type="breaking",
                    category="response",
                    path=path,
                    method=method.upper(),
                    field_name=f"Response {status_code}",
                    message=get_rule_message("success_response_removed"),
                    details=details,
                )
            else:
                return Change(
                    type="potentially_breaking",
                    category="response",
                    path=path,
                    method=method.upper(),
                    field_name=f"Response {status_code}",
                    message=get_rule_message("non_2xx_response_removed"),
                    details=details,
                )
        elif change_type == "added":
            return Change(
                type="non_breaking",
                category="response",
                path=path,
                method=method.upper(),
                field_name=f"Response {status_code}",
                message=get_rule_message("response_added"),
                details=details,
            )
        else:
            return Change(
                type="potentially_breaking",
                category="response",
                path=path,
                method=method.upper(),
                field_name=f"Response {status_code}",
                message="Response changed",
                details=details,
            )