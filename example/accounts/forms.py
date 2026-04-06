from django import forms
from .models import ToolRequest

class ToolRequestForm(forms.ModelForm):

    class Meta:
        model = ToolRequest

        # REMOVED: fixed_value, raw_material, joint_type
        fields = [
            "description",
            "supplier1",
            "supplier2",
            "supplier_code1",
            "supplier_code2",
            "bore_size",
            "boring_teeth",
            "boring_length",
            "diameter",
            "milling_teeth",
            "milling_length",
            "remark",
        ]

        widgets = {
            "description": forms.Select(attrs={"class": "form-select"}),
            "supplier1": forms.Select(attrs={"class": "form-select"}),
            "supplier2": forms.Select(attrs={"class": "form-select"}),
            "bore_size": forms.NumberInput(attrs={"class": "form-control"}),
            "boring_teeth": forms.NumberInput(attrs={"class": "form-control"}),
            "boring_length": forms.NumberInput(attrs={"class": "form-control"}),
            "diameter": forms.NumberInput(attrs={"class": "form-control"}),
            "milling_teeth": forms.NumberInput(attrs={"class": "form-control"}),
            "milling_length": forms.NumberInput(attrs={"class": "form-control"}),
            "remark": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        # FIXED INDENTATION (4 spaces)
        cleaned_data = super().clean()

        description = cleaned_data.get("description")

        bore_size = cleaned_data.get("bore_size")
        boring_teeth = cleaned_data.get("boring_teeth")
        boring_length = cleaned_data.get("boring_length")

        diameter = cleaned_data.get("diameter")
        milling_teeth = cleaned_data.get("milling_teeth")
        milling_length = cleaned_data.get("milling_length")

        supplier1 = cleaned_data.get("supplier1")
        supplier2 = cleaned_data.get("supplier2")

        # Supplier validation
        if supplier1 and supplier2 and supplier1 == supplier2:
            self.add_error("supplier2", "Supplier 2 cannot be the same as Supplier 1")

        # Tool specific validation
        if description:
            name = description.field_name.upper()

            if name == "BORING TOOL HOLDER":
                if not bore_size:
                    self.add_error("bore_size", "Bore size is required")
                if not boring_teeth:
                    self.add_error("boring_teeth", "No. of teeth is required")
                if not boring_length:
                    self.add_error("boring_length", "Length is required")

            if name == "MILLING TOOL":
                if not diameter:
                    self.add_error("diameter", "Diameter is required")
                if not milling_teeth:
                    self.add_error("milling_teeth", "No. of teeth is required")
                if not milling_length:
                    self.add_error("milling_length", "Length is required")

        return cleaned_data