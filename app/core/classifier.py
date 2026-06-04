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
    def _method(method: str) -> Optional[str]:
        """Format an HTTP method when a change belongs to an operation."""
        return method.upper() if method else None

    @staticmethod
    def _merge_details(
        base_details: Optional[Dict[str, Any]] = None,
        extra_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Merge change detail dictionaries while omitting empty values."""
        details = {}
        for source in (base_details or {}, extra_details or {}):
            for key, value in source.items():
                if value is not None and value != "":
                    details[key] = value
        return details

    @staticmethod
    def classify_endpoint_removal(
        path: str, details: Optional[Dict[str, Any]] = None
    ) -> Change:
        """Classify endpoint removal as breaking."""
        return Change(
            type="breaking",
            category="endpoint",
            path=path,
            message=get_rule_message("endpoint_removed"),
            details=Classifier._merge_details(details),
        )

    @staticmethod
    def classify_endpoint_addition(
        path: str, details: Optional[Dict[str, Any]] = None
    ) -> Change:
        """Classify endpoint addition as non-breaking."""
        return Change(
            type="non_breaking",
            category="endpoint",
            path=path,
            message=get_rule_message("endpoint_added"),
            details=Classifier._merge_details(details),
        )

    @staticmethod
    def classify_method_removal(
        path: str, method: str, details: Optional[Dict[str, Any]] = None
    ) -> Change:
        """Classify method removal as breaking."""
        return Change(
            type="breaking",
            category="method",
            path=path,
            method=method.upper(),
            message=get_rule_message("method_removed"),
            details=Classifier._merge_details(details),
        )

    @staticmethod
    def classify_method_addition(
        path: str, method: str, details: Optional[Dict[str, Any]] = None
    ) -> Change:
        """Classify method addition as non-breaking."""
        return Change(
            type="non_breaking",
            category="method",
            path=path,
            method=method.upper(),
            message=get_rule_message("method_added"),
            details=Classifier._merge_details(details),
        )

    @staticmethod
    def classify_parameter_change(
        path: str,
        method: str,
        param_name: str,
        change_type: str,
        is_required: bool = False,
        param_in: str = "",
        old_type: Any = "",
        new_type: Any = "",
        details: Optional[Dict[str, Any]] = None,
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
        base_details = {}
        if param_in:
            base_details["location"] = param_in
        details = Classifier._merge_details(base_details, details)

        if change_type == "removed":
            return Change(
                type="breaking",
                category="parameter",
                path=path,
                method=Classifier._method(method),
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
                    method=Classifier._method(method),
                    field_name=param_name,
                    message=get_rule_message("required_parameter_added"),
                    details=details,
                )
            else:
                return Change(
                    type="non_breaking",
                    category="parameter",
                    path=path,
                    method=Classifier._method(method),
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
                method=Classifier._method(method),
                field_name=param_name,
                message=get_rule_message("parameter_type_changed"),
                details=details,
            )
        elif change_type == "made_required":
            return Change(
                type="breaking",
                category="parameter",
                path=path,
                method=Classifier._method(method),
                field_name=param_name,
                message=get_rule_message("parameter_made_required"),
                details=details,
            )
        elif change_type == "made_optional":
            return Change(
                type="potentially_breaking",
                category="parameter",
                path=path,
                method=Classifier._method(method),
                field_name=param_name,
                message=get_rule_message("parameter_made_optional"),
                details=details,
            )
        else:
            return Change(
                type="potentially_breaking",
                category="parameter",
                path=path,
                method=Classifier._method(method),
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
        details: Optional[Dict[str, Any]] = None,
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
        base_details = {}
        if content_type:
            base_details["content_type"] = content_type
        details = Classifier._merge_details(base_details, details)

        if change_type == "removed":
            return Change(
                type="breaking",
                category="request_body",
                path=path,
                method=Classifier._method(method),
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
                    method=Classifier._method(method),
                    message=get_rule_message("required_request_body_added"),
                    details=details,
                )
            else:
                return Change(
                    type="non_breaking",
                    category="request_body",
                    path=path,
                    method=Classifier._method(method),
                    message=get_rule_message("optional_request_body_added"),
                    details=details,
                )
        elif change_type == "made_required":
            return Change(
                type="breaking",
                category="request_body",
                path=path,
                method=Classifier._method(method),
                message=get_rule_message("request_body_made_required"),
                details=details,
            )
        elif change_type == "made_optional":
            return Change(
                type="potentially_breaking",
                category="request_body",
                path=path,
                method=Classifier._method(method),
                message=get_rule_message("request_body_made_optional"),
                details=details,
            )
        else:
            return Change(
                type="potentially_breaking",
                category="request_body",
                path=path,
                method=Classifier._method(method),
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
        old_type: Any = "",
        new_type: Any = "",
        details: Optional[Dict[str, Any]] = None,
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
        category = "component_schema" if location == "component_schema" else "schema"

        details = Classifier._merge_details({"location": location}, details)

        if change_type == "removed":
            return Change(
                type="breaking",
                category=category,
                path=path,
                method=Classifier._method(method),
                field_name=field_name,
                message=get_rule_message("field_removed"),
                details=details,
            )
        elif change_type == "added":
            details["required"] = is_required
            if is_required and not is_response:
                # Required fields in request body are breaking
                return Change(
                    type="breaking",
                    category=category,
                    path=path,
                    method=Classifier._method(method),
                    field_name=field_name,
                    message=get_rule_message("required_field_added"),
                    details=details,
                )
            else:
                # Optional fields or response fields are non-breaking
                return Change(
                    type="non_breaking",
                    category=category,
                    path=path,
                    method=Classifier._method(method),
                    field_name=field_name,
                    message=get_rule_message("optional_field_added"),
                    details=details,
                )
        elif change_type == "type_changed":
            if old_type:
                details["old_type"] = old_type
            if new_type:
                details["new_type"] = new_type
            return Change(
                type="breaking",
                category=category,
                path=path,
                method=Classifier._method(method),
                field_name=field_name,
                message=get_rule_message("field_type_changed"),
                details=details,
            )
        elif change_type == "made_required":
            if not is_response:
                # Making request field required is breaking
                return Change(
                    type="breaking",
                    category=category,
                    path=path,
                    method=Classifier._method(method),
                    field_name=field_name,
                    message=get_rule_message("field_made_required"),
                    details=details,
                )
            else:
                # Making response field required is potentially breaking
                return Change(
                    type="potentially_breaking",
                    category=category,
                    path=path,
                    method=Classifier._method(method),
                    field_name=field_name,
                    message=get_rule_message("field_made_required"),
                    details=details,
                )
        elif change_type == "made_optional":
            return Change(
                type="potentially_breaking",
                category=category,
                path=path,
                method=Classifier._method(method),
                field_name=field_name,
                message=get_rule_message("field_made_optional"),
                details=details,
            )
        else:
            return Change(
                type="potentially_breaking",
                category=category,
                path=path,
                method=Classifier._method(method),
                field_name=field_name,
                message="Field changed",
                details=details,
            )

    @staticmethod
    def classify_schema_constraint_change(
        path: str,
        method: str,
        field_name: str,
        change_type: str,
        location: str,
        keyword: str,
        old_value: Any = None,
        new_value: Any = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Change:
        """
        Classify JSON Schema keyword and constraint changes.

        Args:
            path: The API path
            method: The HTTP method
            field_name: The field or schema node name
            change_type: Type of constraint change
            location: Location of the schema change
            keyword: JSON Schema keyword that changed
            old_value: Previous keyword value
            new_value: New keyword value
            details: Extra change details

        Returns:
            Classified change
        """
        rule_by_change_type = {
            "enum_value_removed": "enum_value_removed",
            "enum_value_added": "enum_value_added",
            "default_removed": "default_value_removed",
            "default_added": "default_value_added",
            "default_changed": "default_value_changed",
            "made_stricter": "constraint_made_stricter",
            "made_looser": "constraint_made_looser",
            "changed": "constraint_changed",
        }
        rule_type = rule_by_change_type.get(change_type, "constraint_changed")

        change_details = Classifier._merge_details(
            {
                "location": location,
                "keyword": keyword,
                "old_value": old_value,
                "new_value": new_value,
            },
            details,
        )

        return Change(
            type=classify_change(rule_type),
            category="schema_constraint",
            path=path,
            method=Classifier._method(method),
            field_name=field_name,
            message=get_rule_message(rule_type),
            details=change_details,
        )

    @staticmethod
    def classify_component_change(
        component_type: str,
        component_name: str,
        change_type: str,
        old_value: Any = None,
        new_value: Any = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Change:
        """Classify reusable OpenAPI component changes."""
        referenced = bool(details and details.get("impacted_operations"))
        if change_type == "removed":
            rule_type = (
                "referenced_component_removed" if referenced else "component_removed"
            )
        elif change_type == "added":
            rule_type = "component_added"
        else:
            rule_type = "component_changed"

        schema_path = (
            details.get("ref")
            if details and details.get("ref")
            else f"#/components/{component_type}/{component_name}"
        )
        change_details = Classifier._merge_details(
            {
                "component_type": component_type,
                "schema_path": schema_path,
                "old_value": old_value,
                "new_value": new_value,
            },
            details,
        )

        return Change(
            type=classify_change(rule_type),
            category="component_schema" if component_type == "schemas" else "component",
            path=schema_path,
            field_name=component_name,
            message=get_rule_message(rule_type),
            details=change_details,
        )

    @staticmethod
    def classify_response_change(
        path: str,
        method: str,
        status_code: str,
        change_type: str,
        details: Optional[Dict[str, Any]] = None,
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
        details = Classifier._merge_details({"status_code": status_code}, details)

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

    @staticmethod
    def classify_media_type_change(
        path: str,
        method: str,
        location: str,
        content_type: str,
        change_type: str,
        status_code: str = "",
        old_value: Any = None,
        new_value: Any = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Change:
        """Classify request or response media type additions/removals."""
        rule_by_location = {
            ("request_body", "removed"): "request_media_type_removed",
            ("request_body", "added"): "request_media_type_added",
            ("response", "removed"): "response_media_type_removed",
            ("response", "added"): "response_media_type_added",
        }
        rule_type = rule_by_location.get((location, change_type), "constraint_changed")
        change_details = Classifier._merge_details(
            {
                "location": location,
                "content_type": content_type,
                "status_code": status_code,
                "old_value": old_value,
                "new_value": new_value,
            },
            details,
        )

        return Change(
            type=classify_change(rule_type),
            category="media_type",
            path=path,
            method=Classifier._method(method),
            field_name=content_type,
            message=get_rule_message(rule_type),
            details=change_details,
        )

    @staticmethod
    def classify_response_header_change(
        path: str,
        method: str,
        status_code: str,
        header_name: str,
        change_type: str,
        old_value: Any = None,
        new_value: Any = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Change:
        """Classify response header additions, removals, and schema changes."""
        rule_by_change_type = {
            "removed": "response_header_removed",
            "added": "response_header_added",
            "changed": "response_header_changed",
        }
        rule_type = rule_by_change_type.get(change_type, "response_header_changed")
        change_details = Classifier._merge_details(
            {
                "location": "response_header",
                "status_code": status_code,
                "header_name": header_name,
                "old_value": old_value,
                "new_value": new_value,
            },
            details,
        )

        return Change(
            type=classify_change(rule_type),
            category="header",
            path=path,
            method=Classifier._method(method),
            field_name=header_name,
            message=get_rule_message(rule_type),
            details=change_details,
        )

    @staticmethod
    def classify_metadata_change(
        path: str,
        field_name: str,
        rule_type: str = "metadata_changed",
        method: str = "",
        category: str = "metadata",
        old_value: Any = None,
        new_value: Any = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Change:
        """Classify OpenAPI metadata changes that can affect clients or tooling."""
        change_details = Classifier._merge_details(
            {
                "keyword": field_name,
                "old_value": old_value,
                "new_value": new_value,
            },
            details,
        )

        return Change(
            type=classify_change(rule_type),
            category=category,
            path=path,
            method=Classifier._method(method),
            field_name=field_name,
            message=get_rule_message(rule_type),
            details=change_details,
        )

    @staticmethod
    def classify_webhook_change(
        webhook_name: str,
        change_type: str,
        method: str = "",
        old_value: Any = None,
        new_value: Any = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Change:
        """Classify top-level webhook additions, removals, and operation changes."""
        rule_by_change_type = {
            "removed": "webhook_removed",
            "added": "webhook_added",
            "changed": "webhook_changed",
            "operation_removed": "webhook_operation_removed",
            "operation_added": "webhook_operation_added",
        }
        rule_type = rule_by_change_type.get(change_type, "webhook_changed")
        change_details = Classifier._merge_details(
            {
                "metadata_scope": "webhook",
                "old_value": old_value,
                "new_value": new_value,
            },
            details,
        )

        return Change(
            type=classify_change(rule_type),
            category="webhook",
            path=webhook_name,
            method=Classifier._method(method),
            field_name=webhook_name,
            message=get_rule_message(rule_type),
            details=change_details,
        )

    @staticmethod
    def classify_callback_change(
        path: str,
        method: str,
        callback_name: str,
        change_type: str,
        expression: str = "",
        callback_method: str = "",
        old_value: Any = None,
        new_value: Any = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Change:
        """Classify operation callback additions, removals, and nested path changes."""
        rule_by_change_type = {
            "removed": "callback_removed",
            "added": "callback_added",
            "changed": "callback_changed",
            "expression_removed": "callback_expression_removed",
            "expression_added": "callback_expression_added",
            "operation_removed": "callback_operation_removed",
            "operation_added": "callback_operation_added",
        }
        rule_type = rule_by_change_type.get(change_type, "callback_changed")
        field_name = callback_name
        if expression:
            field_name = f"{callback_name} {expression}"

        change_details = Classifier._merge_details(
            {
                "metadata_scope": "callback",
                "callback_name": callback_name,
                "callback_expression": expression,
                "callback_method": callback_method.upper() if callback_method else "",
                "old_value": old_value,
                "new_value": new_value,
            },
            details,
        )

        return Change(
            type=classify_change(rule_type),
            category="callback",
            path=path,
            method=Classifier._method(method),
            field_name=field_name,
            message=get_rule_message(rule_type),
            details=change_details,
        )

    @staticmethod
    def classify_parameter_serialization_change(
        path: str,
        method: str,
        param_name: str,
        param_in: str,
        keyword: str,
        old_value: Any = None,
        new_value: Any = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Change:
        """Classify request parameter serialization metadata changes."""
        change_details = Classifier._merge_details(
            {
                "location": param_in,
                "keyword": keyword,
                "old_value": old_value,
                "new_value": new_value,
            },
            details,
        )

        return Change(
            type=classify_change("parameter_serialization_changed"),
            category="parameter_serialization",
            path=path,
            method=Classifier._method(method),
            field_name=param_name,
            message=get_rule_message("parameter_serialization_changed"),
            details=change_details,
        )
