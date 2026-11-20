import unittest

from api.routers.studio import SAMPLE_APPS, Dashboard, verify_dashboard


class StudioTest(unittest.TestCase):
    def test_installed_samples_pass_the_same_validation_as_generated_views(self):
        for sample in SAMPLE_APPS:
            view = Dashboard.model_validate(SAMPLE_APPS[sample]["initial"])
            verify_dashboard(sample, view)

    def test_numeric_field_comparison_and_unknown_fields(self):
        view = Dashboard.model_validate(SAMPLE_APPS["inventory"]["initial"] | {
            "filters": [{"field": "stock", "op": "lt", "value": None, "compare_field": "reorderPoint"}]
        })
        verify_dashboard("inventory", view)
        view.columns.append("secret")
        with self.assertRaises(ValueError):
            verify_dashboard("inventory", view)



    def test_custom_app_requires_safe_unique_field_keys(self):
        from api.routers.zeta import CustomApp

        draft = {
            "name": "Project Tracker", "description": "Track assignments.", "entity": "Projects",
            "fields": [{"key": "name", "label": "Name", "type": "text"}],
        }
        self.assertEqual(CustomApp.model_validate(draft).fields[0].key, "name")
        draft["fields"].append({"key": "name", "label": "Other name", "type": "text"})
        with self.assertRaises(ValueError):
            CustomApp.model_validate(draft)
        draft["fields"][1]["key"] = "__proto__"
        with self.assertRaises(ValueError):
            CustomApp.model_validate(draft)

    def test_custom_revision_preserves_existing_field_types(self):
        from api.routers.zeta import CustomApp, verify_revision

        source = {"name": "Project Tracker", "description": "Track assignments.", "entity": "Projects"}
        previous = CustomApp.model_validate(source | {"fields": [{"key": "name", "label": "Name", "type": "text"}]})
        changed = CustomApp.model_validate(source | {"fields": [{"key": "name", "label": "Name", "type": "number"}]})
        with self.assertRaises(ValueError):
            verify_revision(previous, changed)
