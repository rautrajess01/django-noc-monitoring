from django import forms
from django.core.exceptions import ValidationError
from .models import NetworkEventImport
import csv
from io import TextIOWrapper
import io

class NetworkEventImportForm(forms.ModelForm):
    class Meta:
        model = NetworkEventImport
        fields = ["csv_file"]
        widgets = {
            "csv_file": forms.FileInput(
                attrs={
                    "accept": ".csv",
                    "class": "form-control",
                    "help_text": "Upload a CSV file with network event data",
                }
            )
        }

    def clean_csv_file(self):
        csv_file = self.cleaned_data.get("csv_file")

        if not csv_file:
            raise ValidationError("Please select a CSV file to upload.")
        
        # ... (your other checks for extension and size are fine) ...

        try:
            # IMPORTANT: Rewind the original file before reading it.
            csv_file.seek(0)
            
            # Read the entire file content into a bytes variable.
            # This leaves the original file object's pointer at the end.
            file_content_bytes = csv_file.read()
            
            # IMPORTANT: Rewind the original file AGAIN so it's ready for saving later.
            csv_file.seek(0)

            # Now, perform validation on a NEW, TEMPORARY in-memory stream.
            # This stream is completely separate from the original `csv_file`.
            text_stream = io.TextIOWrapper(io.BytesIO(file_content_bytes), encoding='utf-8')
            reader = csv.DictReader(text_stream)

            # ... (the rest of your validation logic is PERFECT and does not need to change) ...
            
            # Example snippet of your validation logic that stays the same:
            actual_headers = reader.fieldnames
            if not actual_headers:
                raise ValidationError("CSV file appears to be empty or has no headers")
            
            critical_headers = ["MPLS/Switch", "Down Time"]
            missing_critical = [h for h in critical_headers if h not in actual_headers]
            if missing_critical:
                raise ValidationError(
                    f"CSV file is missing critical headers: {', '.join(missing_critical)}. "
                    f"Found headers: {', '.join(actual_headers)}"
                )
            
            # ... etc ...

        except UnicodeDecodeError:
            raise ValidationError(
                "Unable to read CSV file. Please ensure it's UTF-8 encoded."
            )
        except csv.Error as e:
            raise ValidationError(f"Invalid CSV file format: {e}")
        except Exception as e:
            raise ValidationError(f"Error validating CSV file: {e}")

        # Return the original, untouched, and rewound csv_file object.
        return csv_file

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add help text and styling
        self.fields["csv_file"].help_text = (
            "Upload a CSV file containing network event data. "
            "Required columns: MPLS/Switch, Down Time. "
            "Supported format: MM/DD/YYYY HH:MM:SS for timestamps."
        )

        # Add CSS classes for better styling
        self.fields["csv_file"].widget.attrs.update(
            {"class": "form-control-file", "style": "margin-bottom: 10px;"}
        )


# Optional: Create a form for manual NetworkEvent entry
from .models import NetworkEvent


class NetworkEventForm(forms.ModelForm):
    class Meta:
        model = NetworkEvent
        fields = [
            "name",
            "down_time",
            "up_time",
            "date",
            "type",
            "region",
            "reason",
            "solar",
            "remarks",
            "category",
            "down_count",
        ]
        widgets = {
            "down_time": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "up_time": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "date": forms.TextInput(attrs={"class": "form-control"}),
            "type": forms.Select(
                attrs={"class": "form-control"},
                choices=[
                    ("", "Select Type"),
                    ("switch", "Switch"),
                    ("mpls", "MPLS"),
                    ("router", "Router"),
                    ("optical", "Optical"),
                ],
            ),
            "region": forms.TextInput(attrs={"class": "form-control"}),
            "reason": forms.TextInput(attrs={"class": "form-control"}),
            "solar": forms.TextInput(attrs={"class": "form-control"}),
            "remarks": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "category": forms.TextInput(attrs={"class": "form-control"}),
            "down_count": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make some fields required
        self.fields["name"].required = True
        self.fields["down_time"].required = True

        # Add help text
        self.fields["name"].help_text = "MPLS/Switch name or identifier"
        self.fields["down_time"].help_text = "When the event started"
        self.fields["up_time"].help_text = (
            "When the event ended (leave empty for ongoing events)"
        )
